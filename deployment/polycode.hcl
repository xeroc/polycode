variable "domain" {
  type = string
}
variable "image_version" {
  type = string
}
variable "registry_auth" {
  type = object({
    username = string
    password = string
  })
}

job "polycode" {
  datacenters = ["de1"]
  type        = "service"

  update {
    auto_revert  = true
    auto_promote = true
    canary       = 1
  }

  group "api" {
    network {
      mode = "bridge"
      port "http" {
        to = 8000
      }
    }
    service {
      name = "polycode-api"
      port = "http"
      tags = [
        "traefik.enable=true",
        "traefik.http.routers.${NOMAD_GROUP_NAME}.tls=true",
        "traefik.http.routers.${NOMAD_GROUP_NAME}.tls.certresolver=letsencrypt",
        "traefik.http.routers.${NOMAD_GROUP_NAME}.rule=(Host(`polycode.${var.domain}`))",
      ]
    }
    task "app" {
      driver = "docker"

      config {
        image   = "ghcr.io/xeroc/polycode:${var.image_version}"
        command = "api"
        auth {
          username = "${var.registry_auth.username}"
          password = "${var.registry_auth.password}"
        }
      }
      env {
        APP_PORT           = NOMAD_PORT_http
        REPO_OWNER         = "chainsquad"
        REPO_NAME          = "chaoscraft"
        PROJECT_IDENTIFIER = 1
      }
      vault {
        policies    = ["polycode"]
        change_mode = "restart"
      }
      template {
        destination = "secrets/config.env"
        data        = <<-EOF
          {{ with secret "secrets/data/polycode" }}
          {{ range $k, $v := .Data.data }}
          {{ $k }}={{ $v | replaceAll "\n" "\\n" }}
          {{ end }}{{ end }}

          {{ with service "polycode-redis" }}{{ with index . 0 }}
          REDIS_HOST={{.Address}}
          REDIS_PORT={{.Port}}
          {{ end }}{{ end }}
        EOF
        env         = true
      }
      resources {
        cpu    = 521
        memory = 1024
      }
    }
  }

  group "worker" {
    network {
      mode = "bridge"
      port "ollama" {
        to = 11434
      }
    }
    ephemeral_disk {
      migrate = true
      size    = 5000
      sticky  = true
    }

    task "app" {
      driver = "docker"

      config {
        image   = "ghcr.io/xeroc/polycode:${var.image_version}"
        command = "worker"
        args    = ["--concurrency", 1]
        ports   = []
        auth {
          username = "${var.registry_auth.username}"
          password = "${var.registry_auth.password}"
        }
        volumes = [
          "local/ssh_config:/etc/ssh/ssh_config",
        ]
      }
      env {
        # DATABASE_URL = "not-yet-implemented"
        REPO_OWNER         = "chainsquad"
        REPO_NAME          = "chaoscraft"
        PROJECT_IDENTIFIER = 1
        DATA_PATH          = "/alloc/data"
        CREWAI_STORAGE_DIR = "/alloc/data"

        CELERY_WORKER_PREFETCH_MULTIPLIER = 1
      }
      vault {
        policies    = ["polycode"]
        change_mode = "restart"
      }
      template {
        destination = "secrets/config.env"
        data        = <<-EOF
          {{ with secret "secrets/data/polycode" }}
          {{ range $k, $v := .Data.data }}
          {{ $k }}={{ $v | replaceAll "\n" "\\n" }}
          {{ end }}{{ end }}

          {{ with service "polycode-redis" }}{{ with index . 0 }}
          REDIS_HOST={{.Address}}
          REDIS_PORT={{.Port}}
          {{ end }}{{ end }}

        EOF
        env         = true
      }

      # template {
      #   destination = "secrets/id"
      #   perms       = "0600"
      #   uid         = 1000
      #   gid         = 1000
      #   data        = "{{ with secret \"secrets/data/polycode\" }}{{ .Data.data.SSH_KEY }}{{ end }}"
      # }

      template {
        destination = "local/ssh_config"
        data        = <<-EOF
          Include /etc/ssh/ssh_config.d/*.conf
          Host *
            SendEnv LANG LC_* COLORTERM NO_COLOR
            HashKnownHosts yes
            GSSAPIAuthentication yes

          # Required for pushing via SSH
          Host github
            Hostname github.com
            User git
            IdentityFile ~/.ssh/id
        EOF
        env         = false
      }
      resources {
        cpu    = 2000
        memory = 4048
      }
    }
    task "ollama" {
      driver = "docker"
      config {
        image = "ollama/ollama"
        ports = ["ollama"]
      }
      env {
        OLLAMA_MODELS = "all-minilm:22m"
      }
      resources {
        cpu    = 2000
        memory = 1024
      }
    }
  }

  group "redis" {
    restart {
      attempts = 3
      interval = "1m"
      delay    = "15s"
      mode     = "fail"
    }
    reschedule {
      attempts       = 0 # unlimited
      delay          = "30s"
      delay_function = "exponential"
      max_delay      = "5m"
      unlimited      = true
    }
    network {
      mode = "bridge"
      port "redis" {
        to = 6379
        # static = 6381
      }
    }
    service {
      name = "polycode-redis"
      port = "redis"
      check {
        name     = "redis service port alive"
        type     = "tcp"
        interval = "10s"
        timeout  = "2s"
      }
    }
    task "redis" {
      driver = "docker"
      config {
        image = "redis"
      }
      resources {
        memory = 64
        cpu    = 120
      }
    }
  }

  group "flower" {
    network {
      mode = "bridge"
      port "http" {}
    }
    service {
      name = "gordon-flower"
      port = "http"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.${NOMAD_GROUP_NAME}.rule=Host(`flower-polycode.${var.domain}`)",
        "traefik.http.routers.${NOMAD_GROUP_NAME}.tls.certresolver=letsencrypt",
        "traefik.http.routers.${NOMAD_GROUP_NAME}.tls=true",
        "traefik.http.routers.${NOMAD_GROUP_NAME}.middlewares=auth",
      ]
    }
    ephemeral_disk {
      size = 300
    }
    task "app" {
      driver = "docker"
      config {
        image = "ghcr.io/xeroc/polycode:${var.image_version}"
        auth {
          username = "${var.registry_auth.username}"
          password = "${var.registry_auth.password}"
        }
        command = "flower"
      }
      env {
        APP_HOST                   = "0.0.0.0"
        APP_PORT                   = NOMAD_PORT_http
        APP_LOGLEVEL               = "info"
        FLOWER_PERSISTENT          = true
        FLOWER_STATE_SAVE_INTERVAL = 10000
        FLOWER_DB                  = "/alloc/data/flower.db"
      }
      vault {
        policies    = ["polycode"]
        change_mode = "restart"
      }
      template {
        destination = "secrets/config.env"
        data        = <<-EOF
          {{ with secret "secrets/data/polycode" }}
          {{ range $k, $v := .Data.data }}
          {{ $k }}={{ $v | replaceAll "\n" "\\n" }}
          {{ end }}{{ end }}

          {{ with service "polycode-redis" }}{{ with index . 0 }}
          REDIS_HOST={{.Address}}
          REDIS_PORT={{.Port}}
          {{ end }}{{ end }}

        EOF
        env         = true
      }
      resources {
        cpu    = 2000
        memory = 512
      }
    }
  }
}
