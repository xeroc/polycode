import { Header } from "./components/Header";
import { Footer } from "./components/Footer";
import Home from "./pages/Home";

export default function App() {
  return (
    <div className="min-h-screen bg-background antialiased font-sans">
      <Header />
      <Home />
      <Footer />
    </div>
  );
}
