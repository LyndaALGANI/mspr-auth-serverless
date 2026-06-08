import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';

const API_BASE = (import.meta.env.VITE_GATEWAY_URL || "").replace(/\/$/, "");

// Shared Layout with Decorative Orbs
function Layout({ children }) {
  return (
    <div className="relative min-h-screen w-full flex flex-col items-center justify-center p-6 bg-[#090a0f] overflow-hidden">
      {/* Background Decorative Orbs */}
      <div className="absolute top-[10%] left-[15%] w-[350px] h-[350px] bg-brand-600/10 rounded-full blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-[10%] right-[15%] w-[350px] h-[350px] bg-[#3b82f6]/10 rounded-full blur-[120px] pointer-events-none"></div>

      <header className="mb-8 text-center animate-fade-in">
        <h1 className="font-title text-4xl font-extrabold tracking-tight bg-gradient-to-r from-brand-300 via-brand-500 to-brand-700 bg-clip-text text-transparent">
          COFRAP
        </h1>
        <p className="text-sm text-gray-400 mt-2">
          Plateforme d'Authentification Sécurisée Serverless
        </p>
      </header>

      <main className="w-full max-w-[460px] bg-white/[0.03] backdrop-blur-xl border border-white/[0.08] rounded-2xl p-8 shadow-2xl z-10">
        {children}
      </main>

      <footer className="mt-8 text-xs text-gray-500 text-center">
      </footer>
    </div>
  );
}

// Navigation Tabs helper
function NavigationTabs({ activeTab }) {
  return (
    <div className="flex bg-black/40 border border-white/[0.06] rounded-xl p-1 mb-6">
      <Link
        to="/register"
        className={`flex-1 text-center py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${
          activeTab === 'register'
            ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20'
            : 'text-gray-400 hover:text-gray-200'
        }`}
      >
        Inscription
      </Link>
      <Link
        to="/login"
        className={`flex-1 text-center py-2.5 text-sm font-semibold rounded-lg transition-all duration-300 ${
          activeTab === 'login'
            ? 'bg-brand-600 text-white shadow-lg shadow-brand-600/20'
            : 'text-gray-400 hover:text-gray-200'
        }`}
      >
        Connexion
      </Link>
    </div>
  );
}

// API Call helper
async function apiCall(endpoint, payload) {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });
    
    const data = await response.json();
    if (!response.ok) {
      return { error: data.error || `Erreur serveur (Status ${response.status})` };
    }
    return data;
  } catch (err) {
    return { error: "Impossible de contacter le serveur OpenFaaS. Vérifiez la configuration de VITE_GATEWAY_URL." };
  }
}

// ===================================
// PAGE : INSCRIPTION (/register)
// ===================================
function Register() {
  const [step, setStep] = useState(1);
  const [username, setUsername] = useState("");
  const [passwordInput, setPasswordInput] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });
  
  const [pwQr, setPwQr] = useState("");
  const [totpQr, setTotpQr] = useState("");
  const [backupCodes, setBackupCodes] = useState([]);

  const showMsg = (text, type = "error") => {
    setMessage({ text, type });
  };

  const validateUsername = (name) => {
    const regex = /^[a-zA-Z0-9_.-]{8,20}$/;
    return regex.test(name);
  };

  const handleStep1 = async (e) => {
    e.preventDefault();
    const cleanUsername = username.trim();
    if (!cleanUsername) return showMsg("Veuillez saisir un nom d'utilisateur");
    if (!validateUsername(cleanUsername)) {
      return showMsg("L'identifiant doit comporter entre 8 et 20 caractères et ne contenir que des lettres, chiffres, _, - ou .");
    }
    
    setLoading(true);
    showMsg("Création du compte...", "info");
    
    const res = await apiCall("/function/generate-password", { username: cleanUsername });
    setLoading(false);
    
    if (res.error) {
      if (res.error === "username_already_exists") {
        showMsg("Cet identifiant est déjà utilisé.", "error");
      } else if (res.error === "invalid_username_format") {
        showMsg("Format d'identifiant invalide.", "error");
      } else {
        showMsg(res.error, "error");
      }
    } else {
      setPwQr(res.qr_code);
      showMsg("Compte initialisé. Scannez le code ci-dessous pour récupérer votre mot de passe.", "success");
      setStep(2);
    }
  };

  const handleStep2 = async (e) => {
    e.preventDefault();
    const cleanPw = passwordInput.trim();
    if (!cleanPw) return showMsg("Veuillez coller le mot de passe");
    if (cleanPw.length !== 24) {
      return showMsg("Le mot de passe doit comporter exactement 24 caractères.");
    }
    
    setLoading(true);
    showMsg("Vérification et initialisation de la double authentification...", "info");

    const res = await apiCall("/function/generate-2fa", { username: username.trim(), password: cleanPw });
    setLoading(false);

    if (res.error) {
      if (res.error === "invalid_password") {
        showMsg("Mot de passe incorrect. Veuillez vérifier et réessayer.", "error");
      } else {
        showMsg(res.error, "error");
      }
    } else {
      setTotpQr(res.qr_code);
      setBackupCodes(res.backup_codes || []);
      showMsg("Veuillez scanner le code TOTP avec votre application 2FA.", "success");
      setStep(3);
    }
  };

  const handleStep3 = async (e) => {
    e.preventDefault();
    const cleanTotp = totpCode.trim();
    if (!cleanTotp) return showMsg("Veuillez saisir le code 2FA");
    if (cleanTotp.length !== 6 || isNaN(cleanTotp)) {
      return showMsg("Le code 2FA doit être un nombre de 6 chiffres.");
    }

    setLoading(true);
    showMsg("Finalisation de l'inscription...", "info");

    const res = await apiCall("/function/authenticate", {
      username: username.trim(),
      password: passwordInput.trim(),
      totp_code: cleanTotp
    });
    setLoading(false);

    if (res.error) {
      if (res.error === "invalid_totp") {
        showMsg("Code 2FA invalide. Veuillez réessayer.", "error");
      } else {
        showMsg(res.error, "error");
      }
    } else {
      showMsg("Compte créé avec succès !", "success");
      setStep(4);
    }
  };

  return (
    <div>
      <NavigationTabs activeTab="register" />

      {step === 1 && (
        <form onSubmit={handleStep1} className="space-y-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-brand-400 bg-brand-600/10 border border-brand-500/20 px-2 py-0.5 rounded-full">
              Étape 1 / 3
            </span>
            <span className="text-xs text-gray-400">Créer un compte</span>
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              Nom d'utilisateur
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ex: jean.dupont"
              className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-brand-600/20"
          >
            {loading ? "Création..." : "Créer le compte"}
          </button>
        </form>
      )}

      {step === 2 && (
        <form onSubmit={handleStep2} className="space-y-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-brand-400 bg-brand-600/10 border border-brand-500/20 px-2 py-0.5 rounded-full">
              Étape 2 / 3
            </span>
            <span className="text-xs text-gray-400">Récupérer le mot de passe</span>
          </div>

          <div className="flex flex-col items-center p-4 bg-white rounded-xl shadow-inner border border-white/10">
            <img
              src={`data:image/png;base64,${pwQr}`}
              alt="QR Password"
              className="w-40 h-40 object-contain"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              Mot de passe (scanné)
            </label>
            <input
              type="password"
              value={passwordInput}
              onChange={(e) => setPasswordInput(e.target.value)}
              placeholder="Saisissez ou collez le mot de passe obtenu"
              className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-brand-600/20"
          >
            {loading ? "Chargement..." : "Continuer"}
          </button>
        </form>
      )}

      {step === 3 && (
        <form onSubmit={handleStep3} className="space-y-5">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[10px] uppercase font-bold tracking-wider text-brand-400 bg-brand-600/10 border border-brand-500/20 px-2 py-0.5 rounded-full">
              Étape 3 / 3
            </span>
            <span className="text-xs text-gray-400">Sécurité 2FA</span>
          </div>

          <div className="flex flex-col items-center p-4 bg-white rounded-xl shadow-inner border border-white/10">
            <img
              src={`data:image/png;base64,${totpQr}`}
              alt="QR TOTP"
              className="w-40 h-40 object-contain"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              Code de sécurité 2FA
            </label>
            <input
              type="text"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              placeholder="ex: 123456"
              maxLength={6}
              className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all text-center font-mono tracking-widest text-lg"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-brand-600/20"
          >
            {loading ? "Validation..." : "Valider et créer le compte"}
          </button>
        </form>
      )}

      {step === 4 && (
        <div className="space-y-6">


          <Link
            to="/login"
            className="block w-full py-3 text-center bg-emerald-600 hover:bg-emerald-700 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-emerald-600/20"
          >
            Se connecter maintenant
          </Link>
        </div>
      )}

      {message.text && (
        <div
          className={`mt-4 p-3.5 rounded-xl text-xs font-medium border leading-relaxed ${
            message.type === 'error'
              ? 'bg-red-500/10 border-red-500/20 text-red-400'
              : message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-brand-500/10 border-brand-500/20 text-brand-400'
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

// ===================================
// PAGE : CONNEXION (/login)
// ===================================
function Login() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });
  const navigate = useNavigate();

  const validateUsername = (name) => {
    const regex = /^[a-zA-Z0-9_.-]{8,20}$/;
    return regex.test(name);
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    const cleanUsername = username.trim();
    const cleanPassword = password.trim();
    const cleanTotp = totpCode.trim();

    if (!cleanUsername || !cleanPassword || !cleanTotp) {
      return setMessage({ text: "Veuillez remplir tous les champs", type: "error" });
    }

    if (!validateUsername(cleanUsername)) {
      return setMessage({ text: "L'identifiant doit comporter entre 8 et 20 caractères et ne contenir que des lettres, chiffres, _, - ou .", type: "error" });
    }

    if (cleanPassword.length !== 24) {
      return setMessage({ text: "Le mot de passe doit comporter exactement 24 caractères.", type: "error" });
    }

    if (cleanTotp.length !== 6 || isNaN(cleanTotp)) {
      return setMessage({ text: "Le code 2FA doit être un nombre de 6 chiffres.", type: "error" });
    }

    setLoading(true);
    setMessage({ text: "Vérification des identifiants...", type: "info" });

    const res = await apiCall("/function/authenticate", {
      username: cleanUsername,
      password: cleanPassword,
      totp_code: cleanTotp
    });
    setLoading(false);

    if (res.error) {
      if (res.expired) {
        setMessage({ text: "Mot de passe expiré. Redirection vers le renouvellement...", type: "error" });
        setTimeout(() => {
          navigate(`/renew?username=${encodeURIComponent(cleanUsername)}`);
        }, 2000);
      } else {
        setMessage({ text: res.error === "invalid_credentials" 
          ? "Identifiants incorrects." 
          : res.error === "invalid_totp"
          ? "Code 2FA invalide."
          : res.error, type: "error" });
      }
    } else {
      setMessage({ text: "✅ Authentification réussie ! Accès accordé.", type: "success" });
    }
  };

  return (
    <div>
      <NavigationTabs activeTab="login" />

      <form onSubmit={handleLogin} className="space-y-5">
        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
            Nom d'utilisateur
          </label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="ex: jean.dupont"
            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all"
          />
        </div>

        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
            Mot de passe
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Entrez votre mot de passe"
            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all"
          />
        </div>

        <div>
          <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
            Code de sécurité 2FA
          </label>
          <input
            type="text"
            value={totpCode}
            onChange={(e) => setTotpCode(e.target.value)}
            placeholder="ex: 123456"
            maxLength={6}
            className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-brand-600/20"
        >
          {loading ? "Connexion..." : "Se connecter"}
        </button>

        <div className="flex justify-between items-center pt-2 text-xs">
          <Link to="/recover" className="text-gray-400 hover:text-brand-400 transition-colors">
            Mot de passe perdu ?
          </Link>
          <Link to="/renew" className="text-gray-400 hover:text-brand-400 transition-colors">
            Renouveler identifiants
          </Link>
        </div>
      </form>

      {message.text && (
        <div
          className={`mt-4 p-3.5 rounded-xl text-xs font-medium border leading-relaxed ${
            message.type === 'error'
              ? 'bg-red-500/10 border-red-500/20 text-red-400'
              : message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-brand-500/10 border-brand-500/20 text-brand-400'
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

// ===================================
// PAGE : RENOUVELLEMENT (/renew)
// ===================================
function Renew() {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });
  const [pwQr, setPwQr] = useState("");
  const [totpQr, setTotpQr] = useState("");
  const [backupCodes, setBackupCodes] = useState([]);
  const location = useLocation();

  // Pre-fill username from redirect
  React.useEffect(() => {
    const params = new URLSearchParams(location.search);
    const user = params.get("username");
    if (user) setUsername(user);
  }, [location]);

  const handleRenew = async (e) => {
    e.preventDefault();
    if (!username.trim()) return setMessage({ text: "Veuillez entrer un nom d'utilisateur", type: "error" });

    setLoading(true);
    setMessage({ text: "Génération du nouveau mot de passe...", type: "info" });

    // 1. Generate new password
    const pwRes = await apiCall("/function/generate-password", { username: username.trim() });
    if (pwRes.error) {
      setLoading(false);
      return setMessage({ text: pwRes.error, type: "error" });
    }

    // 2. Generate new 2FA
    setMessage({ text: "Génération de la nouvelle clé 2FA...", type: "info" });
    const totpRes = await apiCall("/function/generate-2fa", { username: username.trim() });
    setLoading(false);

    if (totpRes.error) {
      return setMessage({ text: totpRes.error, type: "error" });
    }

    setPwQr(pwRes.qr_code);
    setTotpQr(totpRes.qr_code);
    setBackupCodes(totpRes.backup_codes || []);
    setMessage({ text: "✅ Vos identifiants ont été renouvelés avec succès !", type: "success" });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4 border-b border-white/[0.06] pb-3">
        <h2 className="font-title text-lg font-semibold text-gray-200">Renouvellement</h2>
        <Link to="/login" className="text-xs text-brand-400 hover:text-brand-300">
          Retour login
        </Link>
      </div>

      {!pwQr ? (
        <form onSubmit={handleRenew} className="space-y-5">
          <p className="text-xs text-gray-400 leading-relaxed">
            Votre mot de passe a expiré ou vous devez le modifier. Saisissez votre identifiant pour générer de nouveaux codes.
          </p>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              Nom d'utilisateur
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ex: jean.dupont"
              className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-brand-600/20"
          >
            {loading ? "Renouvellement..." : "Générer nouveaux identifiants"}
          </button>
        </form>
      ) : (
        <div className="space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="flex flex-col items-center p-3 bg-white rounded-xl">
              <span className="text-[9px] uppercase font-bold text-gray-600 mb-1">Nouveau Password</span>
              <img src={`data:image/png;base64,${pwQr}`} alt="New Password QR" className="w-28 h-28 object-contain" />
            </div>
            <div className="flex flex-col items-center p-3 bg-white rounded-xl">
              <span className="text-[9px] uppercase font-bold text-gray-600 mb-1">Nouveau 2FA</span>
              <img src={`data:image/png;base64,${totpQr}`} alt="New TOTP QR" className="w-28 h-28 object-contain" />
            </div>
          </div>



          <Link
            to="/login"
            className="block w-full py-3 text-center bg-emerald-600 hover:bg-emerald-700 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-emerald-600/20"
          >
            Se connecter avec les nouveaux codes
          </Link>
        </div>
      )}

      {message.text && (
        <div
          className={`mt-4 p-3.5 rounded-xl text-xs font-medium border leading-relaxed ${
            message.type === 'error'
              ? 'bg-red-500/10 border-red-500/20 text-red-400'
              : message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-brand-500/10 border-brand-500/20 text-brand-400'
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

// ===================================
// PAGE : CODE DE SECOURS (/recover)
// ===================================
function Recover() {
  const [username, setUsername] = useState("");
  const [backupCode, setBackupCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: "", type: "" });
  const [pwQr, setPwQr] = useState("");

  const handleRecover = async (e) => {
    e.preventDefault();
    if (!username.trim() || !backupCode.trim()) {
      return setMessage({ text: "Veuillez remplir tous les champs", type: "error" });
    }

    setLoading(true);
    setMessage({ text: "Validation du code de secours...", type: "info" });

    const res = await apiCall("/function/recover-with-backup-code", {
      username: username.trim(),
      backup_code: backupCode.trim()
    });
    setLoading(false);

    if (res.error) {
      setMessage({ text: res.error === "invalid_backup_code" ? "Code de secours invalide ou déjà utilisé." : res.error, type: "error" });
    } else {
      setPwQr(res.qr_code);
      setMessage({ text: "✅ Code validé ! Scannez le QR ci-dessous pour votre nouveau mot de passe.", type: "success" });
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4 border-b border-white/[0.06] pb-3">
        <h2 className="font-title text-lg font-semibold text-gray-200">Récupération</h2>
        <Link to="/login" className="text-xs text-brand-400 hover:text-brand-300">
          Retour login
        </Link>
      </div>

      {!pwQr ? (
        <form onSubmit={handleRecover} className="space-y-5">
          <p className="text-xs text-gray-400 leading-relaxed">
            Utilisez l'un des 5 codes de secours générés lors de votre inscription pour réinitialiser votre mot de passe.
          </p>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              Nom d'utilisateur
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="ex: jean.dupont"
              className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all"
            />
          </div>

          <div>
            <label className="block text-xs font-bold uppercase tracking-wider text-gray-400 mb-2">
              Code de secours
            </label>
            <input
              type="text"
              value={backupCode}
              onChange={(e) => setBackupCode(e.target.value)}
              placeholder="Saisissez votre code à 8 caractères"
              className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 text-sm focus:border-brand-600 focus:ring-1 focus:ring-brand-600 outline-none transition-all font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-brand-600/20"
          >
            {loading ? "Vérification..." : "Valider le code de secours"}
          </button>
        </form>
      ) : (
        <div className="space-y-6">
          <div className="flex flex-col items-center p-4 bg-white rounded-xl">
            <span className="text-xs font-bold text-gray-700 mb-2">Nouveau Mot de Passe (QR)</span>
            <img src={`data:image/png;base64,${pwQr}`} alt="New Password QR" className="w-40 h-40 object-contain" />
          </div>

          <Link
            to="/login"
            className="block w-full py-3 text-center bg-emerald-600 hover:bg-emerald-700 text-sm font-semibold rounded-xl transition-all shadow-lg shadow-emerald-600/20"
          >
            Se connecter
          </Link>
        </div>
      )}

      {message.text && (
        <div
          className={`mt-4 p-3.5 rounded-xl text-xs font-medium border leading-relaxed ${
            message.type === 'error'
              ? 'bg-red-500/10 border-red-500/20 text-red-400'
              : message.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
              : 'bg-brand-500/10 border-brand-500/20 text-brand-400'
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}

// ===================================
// ROUTEUR PRINCIPAL DE L'APPLICATION
// ===================================
export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Login />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/renew" element={<Renew />} />
          <Route path="/recover" element={<Recover />} />
          <Route path="*" element={<Login />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
