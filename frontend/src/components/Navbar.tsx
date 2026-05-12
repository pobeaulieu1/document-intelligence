import { useNavigate, useLocation } from "react-router-dom";
import { Upload, ReceiptText, Shield, Cpu } from "lucide-react";
import { t } from "../theme";

interface Props {
  onUpload: () => void;
}

export function Navbar({ onUpload }: Props) {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  const navLink = (label: string, icon: React.ReactNode, to: string) => {
    const active = pathname === to || pathname.startsWith(to + "/");
    return (
      <button
        onClick={() => navigate(to)}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
          ${active ? "bg-brand-50 text-brand-700" : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"}`}
      >
        {icon}
        {label}
      </button>
    );
  };

  return (
    <header className="bg-white border-b border-gray-100 shrink-0">
      <div className="max-w-7xl mx-auto px-6 h-14 flex items-center">
        {/* Brand */}
        <button
          onClick={() => navigate("/")}
          className="flex items-center gap-2.5 hover:opacity-80 transition-opacity mr-auto"
        >
          <div className="w-7 h-7 rounded-lg bg-brand-600 flex items-center justify-center">
            <ReceiptText size={14} className="text-white" />
          </div>
          <span className="text-sm font-semibold text-gray-900">Expense Intelligence</span>
        </button>

        {/* Right side: nav links + action */}
        <nav className="flex items-center gap-1 mr-3">
          {navLink("Expense Policy", <Shield size={14} />, "/policy")}
          {navLink("AI Pipeline", <Cpu size={14} />, "/pipeline")}
        </nav>

        <button onClick={onUpload} className={t.btnPrimary}>
          <Upload size={14} />
          Upload Receipt
        </button>
      </div>
    </header>
  );
}
