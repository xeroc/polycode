import { Code2 } from "lucide-react";

export function Footer() {
  return (
    <footer className="border-t border-border/50">
      <div className="container mx-auto max-w-6xl px-6 py-12">
        <div className="grid md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Code2 className="h-5 w-5 text-primary" />
              <span className="font-semibold uppercase tracking-[0.3em]">
                POLYCODE
              </span>
            </div>
            <p className="text-sm text-muted-foreground">
              Crafted by ChainSquad GmbH. Specialized, Simple, Fast.
            </p>
          </div>
          <div></div>
          <div>
            <div className="font-medium text-sm mb-4">Resources</div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <a
                  href="#tbd"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover:text-foreground transition-colors"
                >
                  GitHub Repository
                </a>
              </li>
            </ul>
          </div>
          <div>
            <div className="font-medium text-sm mb-4">Legal</div>
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li>
                <a
                  href="https://chainsquad.com/#/privacy"
                  className="hover:text-foreground transition-colors"
                >
                  Privacy Policy
                </a>
              </li>
              <li>
                <a
                  href="https://chainsquad.com/#/legal"
                  className="hover:text-foreground transition-colors"
                >
                  Legal Notice & Terms
                </a>
              </li>
            </ul>
          </div>
        </div>
        <div className="text-center text-sm text-muted-foreground/60 mt-8">
          &copy; 2026 ChainSquad GmbH. Built with ❤️ by polycode
        </div>
      </div>
    </footer>
  );
}
