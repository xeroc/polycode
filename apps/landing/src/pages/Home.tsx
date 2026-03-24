"use client";

import {
  Github,
  ArrowRight,
  Check,
  Zap,
  CheckCircle2,
  ChevronRight,
  Puzzle,
  Lock,
  GitBranch,
  Layers,
} from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";
import { addToWaitlist } from "../lib/n8n";

const features = [
  {
    icon: Zap,
    title: "Label-Driven Workflows",
    description:
      "Add a GitHub label like 'polycode:implement' and AI agents automatically plan, code, test, and create a PR.",
  },
  {
    icon: Puzzle,
    title: "Plugin Architecture",
    description:
      "Extend with Python modules. Import flows from any GitHub repo. Build custom workflows for your team's process.",
  },
  {
    icon: Lock,
    title: "Self-Hosted & Open Source",
    description:
      "MIT licensed core. Your code stays on your infrastructure. Full audit trail with per-story commits.",
  },
];

const workflows = [
  {
    cmd: "polycode flow run ralph --issue 123",
    branch: "feature/auth-middleware",
    description: "Ralph Flow: Plan → Implement → Verify → PR → Merge",
  },
  {
    cmd: "gh issue create --label polycode:implement",
    branch: "feat/new-dashboard",
    description: "Label-triggered: Just add a label, agents handle the rest",
  },
  {
    cmd: "polycode flow list",
    branch: "Available flows",
    description: "Browse built-in and custom flows from your plugins",
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

const extensibility = [
  {
    title: "Write Custom Flows",
    description: "Python-based flows with full access to tools and state",
    icon: GitBranch,
  },
  {
    title: "Plugin Hooks",
    description: "5 lifecycle events for commit, push, PR, merge, cleanup",
    icon: Layers,
  },
  {
    title: "Import from GitHub",
    description: "Share flows across your org or the community",
    icon: Github,
  },
];

const comparison = [
  { feature: "Hosting", devin: "SaaS only", polycode: "Self-hosted" },
  { feature: "Workflows", devin: "Black box", polycode: "Fully customizable" },
  { feature: "Interface", devin: "Chat / Slack", polycode: "GitHub-native" },
  { feature: "Data", devin: "Vendor owns", polycode: "You own" },
  { feature: "Price", devin: "$500/mo", polycode: "Open source (MIT)" },
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
      {/* Hero Section */}
      <section className="py-20">
        <div className="flex items-center gap-2 mb-6">
          <span className="bg-green-500/10 text-green-600 border-green-500/20 text-xs font-medium px-2.5 py-1 border">
            MIT Licensed
          </span>
          <span className="text-muted-foreground text-xs">
            Open Source Core
          </span>
        </div>
        <div className="grid gap-8 lg:grid-cols-[2fr_1fr] lg:gap-16">
          <div className="flex flex-col items-start gap-4 text-left">
            <h1 className="text-3xl font-bold leading-snug tracking-tighter md:text-4xl">
              Label an issue.
              <br />
              <span className="bg-linear-to-r from-blue-500 to-[#14F195] bg-clip-text text-transparent">
                Ship a feature.
              </span>
            </h1>
            <p className="text-lg text-muted-foreground">
              Self-hosted GitHub automation with AI agents. Extensible plugin
              architecture. Your code, your infrastructure, your workflows.
            </p>
            <div className="flex gap-3 pt-2">
              <a
                href="https://github.com/xeroc/polycode"
                target="_blank"
                rel="noopener noreferrer"
                className="bg-primary text-primary-foreground shadow-2xs hover:bg-primary/90 inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-none font-medium text-sm outline-hidden transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 h-11 px-6"
              >
                <Github className="h-4 w-4" />
                View on GitHub
              </a>
              <a
                href="#how-it-works"
                className="border bg-background hover:bg-accent hover:text-accent-foreground inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-none font-medium text-sm outline-hidden transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 h-11 px-6"
              >
                See How It Works
                <ArrowRight className="h-4 w-4" />
              </a>
            </div>
          </div>
          <div className="flex flex-col justify-center gap-4">
            <div className="bg-card border-border rounded-lg border p-4 space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">$</span>
                <span className="text-foreground text-xs">
                  polycode flow run ralph --issue 42
                </span>
              </div>
              <div className="space-y-1 mt-2 pl-4">
                <div className="flex items-center gap-2 text-xs text-green-500">
                  <Check className="h-3 w-3" />
                  <span>Planning user stories...</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-green-500">
                  <Check className="h-3 w-3" />
                  <span>Implementing story 1/3...</span>
                </div>
                <div className="flex items-center gap-2 text-xs text-blue-500">
                  <span className="animate-pulse">●</span>
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

      {/* Features Section */}
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

      {/* Extensibility Section */}
      <section className="py-20" id="plugins">
        <div className="flex items-center gap-3 mb-8">
          <Puzzle className="h-5 w-5 text-primary" />
          <h2 className="text-2xl font-bold">Plugin Architecture</h2>
        </div>
        <p className="text-muted-foreground mb-8 max-w-2xl">
          Polycode is designed for extensibility. Write custom flows in Python,
          register hooks for lifecycle events, and share workflows across your
          organization or with the community.
        </p>
        <div className="grid gap-4 md:grid-cols-3">
          {extensibility.map((item, index) => (
            <motion.div
              key={item.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className="bg-card border-border rounded-lg border p-4 space-y-2"
            >
              <item.icon className="h-5 w-5 text-primary" />
              <h3 className="font-medium text-sm">{item.title}</h3>
              <p className="text-xs text-muted-foreground">
                {item.description}
              </p>
            </motion.div>
          ))}
        </div>
        <div className="mt-6 bg-muted/30 border-border rounded-lg border p-4">
          <p className="text-xs font-mono text-muted-foreground mb-2">
            # .polycode/polycode.yml
          </p>
          <pre className="text-xs text-foreground overflow-x-auto">
            {`flows:
  ralph:
    label: implement
    source: polycode/ralph  # built-in

  deploy-check:
    label: deploy-check
    source: github:acme-org/polycode-flows/deploy  # from GitHub`}
          </pre>
        </div>
      </section>

      <div
        className="font-mono text-sm text-muted-foreground/30 select-none"
        aria-hidden="true"
      >
        //
      </div>

      {/* How It Works Section */}
      <section className="py-20" id="how-it-works">
        <h2 className="text-2xl font-bold mb-8">How It Works</h2>
        <div className="grid gap-4 md:grid-cols-3">
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

      {/* Comparison Section */}
      <section className="py-20" id="comparison">
        <h2 className="text-2xl font-bold mb-8">Why Polycode?</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 font-medium">Feature</th>
                <th className="text-left py-3 font-medium text-muted-foreground">
                  Devin
                </th>
                <th className="text-left py-3 font-medium text-primary">
                  Polycode
                </th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((row) => (
                <tr key={row.feature} className="border-b border-border/50">
                  <td className="py-3 font-medium">{row.feature}</td>
                  <td className="py-3 text-muted-foreground">{row.devin}</td>
                  <td className="py-3 text-primary">{row.polycode}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-muted-foreground text-sm mt-6">
          Devin is built for demos. Polycode is built for teams that want
          automation they can trust, inspect, and extend.
        </p>
      </section>

      <div
        className="font-mono text-sm text-muted-foreground/30 select-none"
        aria-hidden="true"
      >
        //
      </div>

      {/* Waitlist Section */}
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

      {/* Tech Stack Section */}
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
