"use client";

import {
  Github,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  Puzzle,
  Lock,
  Target,
  Route,
  Cpu,
  MessageSquare,
  ListChecks,
  GitPullRequest,
  Shield,
  PlayCircle,
  Network,
  FileCheck2,
  Repeat,
} from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";
import { addToWaitlist } from "../lib/n8n";

const pillars = [
  {
    icon: GitPullRequest,
    title: "PR-First System",
    badge: "Core Differentiator",
    description:
      "Every PR feels like a top-tier engineer wrote it. Clean atomic commits, rich descriptions with what changed, why, and how. Git notes attach decision metadata without polluting history.",
    details: [
      "Structured PR descriptions: what, why, how",
      "Git notes for decision reasoning and rejected approaches",
      "Linked issues with checklist sync",
    ],
  },
  {
    icon: Repeat,
    title: "Reproducible Workflows",
    badge: null,
    description:
      "Bounded, inspectable behavior. Fixed flow stages, retry limits, structured I/O between crews. Re-run any flow with the same config and get comparable results.",
    details: [
      "Flow versioning in every run",
      "Structured inputs/outputs between stages",
      "Re-run with identical configuration",
    ],
  },
  // {
  //   icon: Puzzle,
  //   title: "Flow Marketplace",
  //   badge: "Platform Play",
  //   description:
  //     "Import flows from any GitHub repo. Version-pin with @v1. Share workflows across your org or the community. Browse, discover, and compose.",
  //   details: [
  //     "GitHub-based imports (github:org/repo)",
  //     "Version pinning per flow",
  //     "Community sharing and discoverability",
  //   ],
  // },
  {
    icon: Shield,
    title: "Policy Engine",
    badge: null,
    description:
      "Don't ask the AI to follow rules — enforce them. Python validators run as pre-commit, post-story, and pre-PR checks. AI that follows your engineering rules by construction.",
    details: [
      "Test coverage enforcement",
      "Forbidden file protection",
      "Dependency rule validation",
    ],
  },
  {
    icon: Puzzle,
    title: "Plugin Architecture",
    badge: null,
    description:
      "Polycode is designed for extensibility. Write custom flows in Python, register hooks for lifecycle events, and share workflows across your organization or with the community.",
    details: [
      "Write Custom Flow",
      "Custom Plugin Hooks and Events",
      "Any project management system",
    ],
  },
  {
    icon: Network,
    title: "Multi-Issue Awareness",
    badge: "Early Differentiator",
    description:
      "During planning, scan other open issues for overlap, shared files, and dependencies. Suggest batch execution and detect conflicts before they happen.",
    details: [
      "Detect overlapping issues",
      "Shared file conflict detection",
      "Dependency graph awareness",
    ],
  },
  {
    icon: FileCheck2,
    title: "GitHub Projects Engine",
    badge: null,
    description:
      "Issue enters 'Ready' → start flow. Labeled 'blocked' → spawn debugging flow. PR merged → auto-trigger follow-ups. Zapier for GitHub Projects.",
    details: [
      "Project status → flow triggers",
      "Automated follow-up workflows",
      "Custom automation rules",
    ],
  },
  // {
  //   icon: Lock,
  //   title: "Self-Hosted & Open Source",
  //   badge: "MIT Licensed",
  //   description:
  //     "Your code stays on your infrastructure. Full audit trail with per-story commits. No vendor lock-in, no code leaving your network.",
  //   details: [
  //     "MIT licensed core",
  //     "Full audit trail",
  //     "Infrastructure you control",
  //   ],
  // },
];

const approachComparison = [
  {
    aspect: "Thinking",
    chat: "Reactive, fast",
    issue: "Deliberate, structured",
  },
  { aspect: "Decisions", chat: "Lost in threads", issue: "Auditable trail" },
  { aspect: "Ownership", chat: "Ambiguous", issue: "Explicit assignees" },
  { aspect: "Context", chat: "Noisy, drifting", issue: "Scoped, clear" },
  { aspect: "At scale", chat: "Falls apart", issue: "Dependencies visible" },
  { aspect: "Over time", chat: "Ephemeral", issue: "Persistent" },
];

const howSteps = [
  {
    step: "01",
    title: "Create an issue",
    description: "Define scope, context, and acceptance criteria",
  },
  {
    step: "02",
    title: "Add a label",
    description: "Trigger a structured AI workflow",
  },
  {
    step: "03",
    title: "Agent executes",
    description: "Plans, implements, tests autonomously",
  },
  {
    step: "04",
    title: "PR closes the loop",
    description: "Full audit trail linked to the issue",
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

const comparison = [
  {
    feature: "Core Model",
    polycode: "Workflow automation system",
    devin: "Autonomous AI engineer",
    openhands: "Agent runtime / chat",
  },
  {
    feature: "Trigger",
    polycode: "GitHub label on issue",
    devin: "Chat prompt / ticket",
    openhands: "Chat / session",
  },
  {
    feature: "Interface",
    polycode: "GitHub-native",
    devin: "Proprietary IDE + chat",
    openhands: "Web UI / API",
  },
  {
    feature: "Hosting",
    polycode: "Self-hosted",
    devin: "SaaS only",
    openhands: "Self-hosted possible",
  },
  {
    feature: "Data Privacy",
    polycode: "Code stays on your infra",
    devin: "Vendor processes code",
    openhands: "Depends on deployment",
  },
  {
    feature: "Workflows",
    polycode: "Deterministic, pluggable flows",
    devin: "Black box autonomy",
    openhands: "Open-ended exploration",
  },
  {
    feature: "Extensibility",
    polycode: "Plugin architecture + hooks",
    devin: "Closed system",
    openhands: "Tool-based, extensible",
  },
  {
    feature: "Auditability",
    polycode: "Per-story commits, full trail",
    devin: "Opaque reasoning",
    openhands: "Session logs",
  },
  {
    feature: "Control",
    polycode: "Bounded retries, lifecycle hooks",
    devin: "Full autonomy, less predictable",
    openhands: "Freeform exploration",
  },
  {
    feature: "Target User",
    polycode: "Engineering teams, DevOps",
    devin: "Individual developers",
    openhands: "Developers + researchers",
  },
  {
    feature: "License",
    polycode: "MIT (open source)",
    devin: "Proprietary ($500/mo)",
    openhands: "Open source",
  },
  {
    feature: "Best For",
    polycode: "Structured, repeatable work",
    devin: "Novel, undefined problems",
    openhands: "Experimentation + research",
  },
];

const positioningCards = [
  {
    title: "Polycode",
    subtitle: "The Factory System",
    description:
      "Label an issue → agents plan, implement, test, and PR. Deterministic pipelines your team trusts. Extensible with plugins and hooks.",
    checks: [
      "GitHub-native triggers",
      "Deterministic lifecycle",
      "Plugin architecture",
      "Full audit trail",
      "Self-hosted, MIT licensed",
    ],
  },
  {
    title: "Devin",
    subtitle: "The AI Employee",
    description:
      "Give it a task, it explores, improvises, and iterates. Powerful for undefined problems, but unpredictable and closed-source.",
    checks: [
      "Full IDE + browser access",
      "Zero setup UX",
      "Can tackle novel problems",
      "Proprietary, SaaS only",
      "Black-box decisions",
    ],
  },
  {
    title: "OpenHands",
    subtitle: "The Agent Sandbox",
    description:
      "General-purpose agent runtime for experimentation and research. Flexible but less opinionated about process.",
    checks: [
      "Open-ended agent sessions",
      "Extensible tool system",
      "Research-oriented",
      "Community-driven",
      "Less structured flows",
    ],
  },
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
                href="#why"
                className="border bg-background hover:bg-accent hover:text-accent-foreground inline-flex cursor-pointer items-center justify-center gap-2 whitespace-nowrap rounded-none font-medium text-sm outline-hidden transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50 h-11 px-6"
              >
                Why Polycode
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

      {/* Golden Circle: Why → How → What */}
      <section className="py-20" id="why">
        {/* WHY */}
        <div className="mb-24">
          <div className="flex items-center gap-2 mb-3">
            <Target className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium uppercase tracking-widest text-primary">
              Why
            </span>
          </div>
          <h2 className="text-2xl font-bold mb-2">Structure beats speed</h2>
          <p className="text-muted-foreground mb-8 max-w-xl">
            Chat-based AI agents are fast but forgetful. We built for teams that
            value clarity, accountability, and durability.
          </p>
          <div className="border border-border rounded-lg overflow-hidden">
            <div className="grid grid-cols-[150px_1fr_1fr]">
              <div className="bg-muted/30 px-4 py-2.5 border-b border-r border-border/50">
                <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                  &nbsp;
                </span>
              </div>
              <div className="bg-muted/30 px-4 py-2.5 border-b border-r border-border/50 flex items-center gap-1.5">
                <MessageSquare className="h-3 w-3 text-muted-foreground" />
                <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">
                  Chat-based
                </span>
              </div>
              <div className="bg-primary/5 px-4 py-2.5 border-b border-border/50 flex items-center gap-1.5">
                <ListChecks className="h-3 w-3 text-primary" />
                <span className="text-[10px] font-medium uppercase tracking-widest text-primary">
                  Issue-driven
                </span>
              </div>
            </div>
            {approachComparison.map((row) => (
              <div
                key={row.aspect}
                className={`grid grid-cols-[150px_1fr_1fr]`}
              >
                <div className="px-4 py-2.5 border-r border-border/50">
                  <span className="text-xs font-medium">{row.aspect}</span>
                </div>
                <div className="px-4 py-2.5 border-r border-border/50">
                  <span className="text-xs text-muted-foreground">
                    {row.chat}
                  </span>
                </div>
                <div className="px-4 py-2.5">
                  <span className="text-xs text-primary font-medium">
                    {row.issue}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* HOW */}
        <div className="mb-24">
          <div className="flex items-center gap-2 mb-3">
            <Route className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium uppercase tracking-widest text-primary">
              How
            </span>
          </div>
          <h2 className="text-2xl font-bold mb-8">
            GitHub as the coordination layer
          </h2>
          <div className="grid gap-4 md:grid-cols-4">
            {howSteps.map((item, index) => (
              <motion.div
                key={item.step}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
                className="bg-card border-border border p-4 space-y-1"
              >
                <span className="text-2xl font-bold text-primary/15 font-mono">
                  {item.step}
                </span>
                <h3 className="font-medium text-sm">{item.title}</h3>
                <p className="text-xs text-muted-foreground">
                  {item.description}
                </p>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Features Section */}
        <div id="features">
          <div className="flex items-center gap-2 mb-3">
            <Cpu className="h-4 w-4 text-primary" />
            <span className="text-xs font-medium uppercase tracking-widest text-primary">
              What
            </span>
          </div>
          <h2 className="text-2xl font-bold mb-2">
            GitHub-native automation engine
          </h2>
          <p className="text-muted-foreground mb-10 max-w-2xl">
            GitHub is the interface. PRs are the output. Flows are the product.
            Everything Polycode does reinforces this loop.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            {pillars.map((pillar, index) => (
              <motion.div
                key={pillar.title}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.05 }}
                className="bg-card border-border border p-5 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <pillar.icon className="h-4 w-4 text-primary shrink-0" />
                    <h3 className="font-medium text-sm">{pillar.title}</h3>
                  </div>
                  {pillar.badge && (
                    <span className="text-[10px] font-medium uppercase tracking-wider text-primary bg-primary/10 px-2 py-0.5 border border-primary/20">
                      {pillar.badge}
                    </span>
                  )}
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  {pillar.description}
                </p>
                <ul className="space-y-1">
                  {pillar.details.map((detail) => (
                    <li
                      key={detail}
                      className="flex items-start gap-2 text-xs text-muted-foreground"
                    >
                      <Check className="h-3 w-3 mt-0.5 shrink-0 text-primary/60" />
                      <span>{detail}</span>
                    </li>
                  ))}
                </ul>
              </motion.div>
            ))}
          </div>
          {/*         <div className="mt-8 bg-muted/30 border-border border p-4"> */}
          {/*           <p className="text-xs font-mono text-muted-foreground mb-2"> */}
          {/*             # .polycode/polycode.yml */}
          {/*           </p> */}
          {/*           <pre className="text-xs text-foreground overflow-x-auto"> */}
          {/*             {`flows: */}
          {/* ralph: */}
          {/*   label: implement */}
          {/*   source: polycode/ralph  # built-in */}
          {/**/}
          {/* deploy-check: */}
          {/*   label: deploy-check */}
          {/*   source: github:acme-org/polycode-flows/deploy@v1  # versioned, from GitHub`} */}
          {/*           </pre> */}
          {/*         </div> */}
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
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-medium uppercase tracking-widest text-primary">
            Compare
          </span>
        </div>
        <h2 className="text-2xl font-bold mb-2">
          Same wave, different philosophy
        </h2>
        <p className="text-muted-foreground mb-12 max-w-2xl">
          Polycode, Devin, and OpenHands all use AI agents to perform software
          engineering tasks. But they're built on fundamentally different
          assumptions about how work should get done.
        </p>

        {/* Positioning Cards */}
        <div className="grid gap-4 md:grid-cols-3 mb-16">
          {positioningCards.map((card, index) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              className={`bg-card border-border border p-6 space-y-4 ${
                card.title === "Polycode"
                  ? "ring-1 ring-primary/30 bg-primary/[0.03]"
                  : ""
              }`}
            >
              <div>
                <span
                  className={`text-[10px] font-medium uppercase tracking-widest ${
                    card.title === "Polycode"
                      ? "text-primary"
                      : "text-muted-foreground"
                  }`}
                >
                  {card.subtitle}
                </span>
                <h3
                  className={`text-lg font-bold ${
                    card.title === "Polycode" ? "text-primary" : ""
                  }`}
                >
                  {card.title}
                </h3>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                {card.description}
              </p>
              <ul className="space-y-1.5">
                {card.checks.map((check) => (
                  <li
                    key={check}
                    className="flex items-start gap-2 text-xs text-muted-foreground"
                  >
                    <Check
                      className={`h-3 w-3 mt-0.5 shrink-0 ${
                        card.title === "Polycode"
                          ? "text-primary"
                          : "text-muted-foreground/50"
                      }`}
                    />
                    <span>{check}</span>
                  </li>
                ))}
              </ul>
            </motion.div>
          ))}
        </div>

        {/* Feature Comparison Table */}
        <h3 className="text-lg font-bold mb-6">Feature comparison</h3>
        <div className="overflow-x-auto border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-muted/30">
                <th className="text-left py-3 px-4 font-medium text-xs uppercase tracking-widest">
                  Feature
                </th>
                <th className="text-left py-3 px-4 font-medium text-primary">
                  Polycode
                </th>
                <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                  Devin
                </th>
                <th className="text-left py-3 px-4 font-medium text-muted-foreground">
                  OpenHands
                </th>
              </tr>
            </thead>
            <tbody>
              {comparison.map((row, i) => (
                <tr
                  key={row.feature}
                  className={`border-b border-border/50 ${
                    i % 2 === 0 ? "bg-muted/10" : ""
                  }`}
                >
                  <td className="py-3 px-4 font-medium text-xs">
                    {row.feature}
                  </td>
                  <td className="py-3 px-4 text-primary text-xs font-medium">
                    {row.polycode}
                  </td>
                  <td className="py-3 px-4 text-muted-foreground text-xs">
                    {row.devin}
                  </td>
                  <td className="py-3 px-4 text-muted-foreground text-xs">
                    {row.openhands}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Bottom Line */}
        <div className="mt-8 border-l-2 border-primary/30 pl-4">
          <p className="text-sm text-muted-foreground">
            <strong className="text-foreground">Bottom line:</strong> Devin is
            an AI employee you chat with. OpenHands is an agent sandbox for
            experimentation. Polycode is{" "}
            <span className="text-primary font-medium">
              CI/CD for AI-driven development workflows
            </span>{" "}
            — deterministic, auditable, and built for engineering teams.
          </p>
        </div>
      </section>

      <div
        className="font-mono text-sm text-muted-foreground/30 select-none"
        aria-hidden="true"
      >
        //
      </div>

      {/* Waitlist Section */}
      <section className="py-20" id="waitlist">
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
      </section>
    </main>
  );
}
