"use client";

import {
  Github,
  ArrowRight,
  Check,
  Terminal,
  Zap,
  CheckCircle2,
  ChevronRight,
} from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";
import { addToWaitlist } from "../lib/n8n";

const features = [
  {
    icon: Zap,
    title: "Fast Iterative Workflows",
    description:
      "Ralph Loop implements changes with automated verification. Fast, reliable, with built-in quality checks.",
  },
  {
    icon: Terminal,
    title: "Multi-Agent Systems",
    description:
      "CrewAI-powered agents collaborate on complex tasks. Each agent specializes in different aspects.",
  },
  {
    icon: Github,
    title: "GitHub App Integration",
    description:
      "Seamless automation across multiple repositories. Label-triggered workflows, webhooks, and PR automation.",
  },
];

const workflows = [
  {
    cmd: "polycode ralph start --issue 123",
    branch: "feature/auth-middleware",
    description:
      "Ralph Flow: Fast iterative implementation with automated verification",
  },
  {
    cmd: "polycode feature-dev create --project acme/web",
    branch: "feat/new-dashboard",
    description:
      "Feature Flow: Comprehensive planning, implementation, testing, and review",
  },
  {
    cmd: "gh issue create --label ralph",
    branch: "bug/performance",
    description:
      "Label-based automation: Just add a label and let agents handle it",
  },
];

const tech = [
  "Python 3.13",
  "CrewAI",
  "FastAPI",
  "Celery",
  "Redis",
  "PostgreSQL",
];

export default function App() {
  const [email, setEmail] = useState("");
  const [isSubmitted, setIsSubmitted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await addToWaitlist({
        email,
        type: "waitlist",
      });
      setIsSubmitted(true);
      console.log("Waitlist signup:", email);
    } catch (err) {
      setError("Something went wrong. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-5xl px-4">
      <section className="py-20">
        <div className="grid gap-8 lg:grid-cols-[2fr_1fr] lg:gap-16">
          <div className="flex flex-col items-start gap-4 text-left">
            <h1 className="text-3xl font-bold leading-snug tracking-tighter md:text-4xl">
              Multi-agent software
              <span className="bg-linear-to-r from-blue-500 to-[#14F195] bg-clip-text text-transparent">
                {" "}
                automation
              </span>
            </h1>
            <p className="text-lg text-muted-foreground">
              Automate software development with AI-powered workflows. GitHub
              App integration, webhook-driven automation, and label-triggered
              flows.
            </p>
            <div className="flex gap-3 pt-2">
              <a
                href="https://github.com/your-repo/polycode"
                target="_blank"
                rel="noopener noreferrer"
                className="bg-primary text-primary-foreground shadow-2xs hover:bg-primary/90 inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-none font-medium text-sm outline-hidden transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 h-11 px-6"
              >
                <Github className="h-4 w-4" />
                Get Started
              </a>
              <a
                href="#how-it-works"
                className="border bg-background hover:bg-accent hover:text-accent-foreground inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-none font-medium text-sm outline-hidden transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 h-11 px-6"
              >
                Learn More
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>
          <div className="flex flex-col justify-center gap-4">
            <div className="bg-card border-border rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">$</span>
                <span className="text-foreground text-xs">
                  polycode ralph start --issue 123
                </span>
              </div>
              <div className="space-y-1 mt-2 pl-4">
                <div className="flex items-center gap-2 text-xs text-green-500">
                  <Check className="h-3 w-3" />
                  <span>Planning tasks...</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-green-500">
                  <Check className="h-3 w-3" />
                  <span>Implementing feature...</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-green-500">
                  <Check className="h-3 w-3" />
                  <span>Running tests...</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
      <div
        className="font-mono text-sm text-muted-foreground/30 select-none"
        aria-hidden="true"
      >
        //
      </div>
      <section id="waitlist" className="mb-24">
        <div className="border border-border/50 p-12">
          <h2 className="text-2xl font-bold mb-4">Join Early Access</h2>
          <p className="text-lg text-muted-foreground mb-6">
            Get notified when we launch beta. Early adopters get free access to
            premium features.
          </p>
          {!isSubmitted ? (
            <form onSubmit={handleSubmit} className="max-w-md">
              <div className="flex gap-2">
                <input
                  type="email"
                  placeholder="your@email.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="bg-input/30 border-input placeholder:text-muted-foreground/50 h-11 w-full border px-4 text-sm transition-colors focus-visible:outline-hidden focus-visible:ring-1 focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                />
                <button
                  type="submit"
                  className="bg-primary text-primary-foreground shadow-2xs hover:bg-primary/90 inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-none font-medium text-sm outline-hidden transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 h-11 px-6"
                  disabled={loading || !email}
                >
                  Join Waitlist
                  <ChevronRight className="h-4 w-4" />
                </button>
                {error && <p className="text-sm text-destructive">{error}</p>}
              </div>
            </form>
          ) : (
            <div className="flex items-center gap-2 text-primary">
              <CheckCircle2 className="h-5 w-5" />
              <span className="font-medium">
                You're on the list! We'll be in touch soon.
              </span>
            </div>
          )}
          <p className="text-xs text-muted-foreground mt-4">
            No spam, ever. Unsubscribe anytime.
          </p>
        </div>
      </section>
      <div
        className="font-mono text-sm text-muted-foreground/30 select-none"
        aria-hidden="true"
      >
        //
      </div>
      <section className="py-20" id="features">
        <div className="grid gap-8 md:grid-cols-3">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="space-y-2"
            >
              <div className="text-primary">
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="font-medium text-sm">{feature.title}</h3>
              <p className="text-sm text-muted-foreground">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </section>
      <div
        className="font-mono text-sm text-muted-foreground/30 select-none"
        aria-hidden="true"
      >
        //
      </div>
      <section className="py-20" id="how-it-works">
        <h2 className="text-2xl font-bold mb-8">How It Works</h2>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {workflows.map((workflow, index) => (
            <motion.div
              key={workflow.cmd}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="bg-card border-border rounded-lg border p-4 space-y-3"
            >
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">$</span>
                <span className="text-foreground text-sm font-mono">
                  {workflow.cmd}
                </span>
              </div>
              <div className="space-y-2 mt-2">
                <div className="text-xs text-muted-foreground">
                  {workflow.branch}
                </div>
                <p className="text-sm text-muted-foreground">
                  {workflow.description}
                </p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>
      <div
        className="font-mono text-sm text-muted-foreground/30 select-none"
        aria-hidden="true"
      >
        //
      </div>
      <section className="py-20" id="tech">
        <h2 className="text-2xl font-bold mb-8">Built With</h2>
        <div className="flex flex-wrap gap-2">
          {tech.map((item) => (
            <span
              key={item}
              className="border-border bg-muted/20 text-muted-foreground px-3 py-1.5 text-sm border"
            >
              {item}
            </span>
          ))}
        </div>
      </section>
    </main>
  );
}
