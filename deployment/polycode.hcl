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
      name = "na"
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
        # DATABASE_URL = "not-yet-implemented"
        APP_PORT           = NOMAD_PORT_http
        REPO_OWNER         = "xeroc"
        REPO_NAME          = "demo"
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
          {{ $k }}={{ $v }}
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
        REPO_OWNER         = "xeroc"
        REPO_NAME          = "demo"
        PROJECT_IDENTIFIER = 1
        DATA_PATH          = "/alloc/data"
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
          {{ $k }}={{ $v }}
          {{ end }}{{ end }}

          {{ with service "polycode-redis" }}{{ with index . 0 }}
          REDIS_HOST={{.Address}}
          REDIS_PORT={{.Port}}
          {{ end }}{{ end }}
        EOF
        env         = true
      }

      template {
        destination = "secrets/id"
        data        = <<-EOF
          {{ with secret "secrets/data/polycode" }}
          {{ .Data.data.SSH_KEY }}
          {{ end }}
        EOF
        env         = true
      }
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
            IdentityFile /secrets/data/polycode
        EOF
        env         = false
      }
      resources {
        cpu    = 2000
        memory = 4048
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
}
