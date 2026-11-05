import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  completePasswordReset,
  login,
  register,
  requestPasswordReset,
  verifyPasswordReset,
} from "../shared/api/auth";

type Mode = "register" | "login" | "reset-email" | "reset-code" | "reset-password";

export default function AuthPage() {
  const [mode, setMode] = useState<Mode>("register");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [code, setCode] = useState("");
  const [resetToken, setResetToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const navigate = useNavigate();

  const copy = {
    register: { title: "Создай свой DAYBOOK", subtitle: "Начни собирать идеи, знания и истории в одном месте.", action: "Продолжить" },
    login: { title: "С возвращением", subtitle: "Войди, чтобы продолжить свой путь.", action: "Войти" },
    "reset-email": { title: "Восстановление пароля", subtitle: "Отправим код подтверждения на твою почту.", action: "Получить код" },
    "reset-code": { title: "Проверь почту", subtitle: "Введи шестизначный код из письма. Он действует 10 минут.", action: "Подтвердить код" },
    "reset-password": { title: "Новый пароль", subtitle: "Придумай новый пароль длиной не менее 8 символов.", action: "Сохранить пароль" },
  }[mode];

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");

    if (mode === "register" && password !== confirmation) {
      setError("Пароли не совпадают.");
      return;
    }
    if ((mode === "register" || mode === "reset-password") && password.length < 8) {
      setError("Пароль должен содержать не менее 8 символов.");
      return;
    }

    setBusy(true);
    try {
      if (mode === "register") {
        await register({ email, password });
        navigate("/profile");
      } else if (mode === "login") {
        await login({ email, password });
        navigate("/profile");
      } else if (mode === "reset-email") {
        await requestPasswordReset(email);
        setMode("reset-code");
        setNotice("Если для этого адреса есть аккаунт, письмо с кодом отправлено.");
      } else if (mode === "reset-code") {
        const result = await verifyPasswordReset(email, code);
        setResetToken(result.token);
        setMode("reset-password");
      } else {
        await completePasswordReset(email, resetToken, password);
        setMode("login");
        setPassword("");
        setConfirmation("");
        setCode("");
        setNotice("Пароль изменён. Теперь войди с новым паролем.");
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось выполнить запрос. Попробуй ещё раз.");
    } finally {
      setBusy(false);
    }
  }

  function changeMode(next: Mode) {
    setMode(next);
    setError("");
    setNotice("");
    setPassword("");
    setConfirmation("");
    setCode("");
  }

  return (
    <section className="auth-layout">
      <div className="auth-intro">
        <p className="eyebrow">PEOPLE · IDEAS · STORIES · GROWTH</p>
        <h1>Every day is a story.</h1>
        <p className="lead">Пространство, где можно узнавать новое, создавать, общаться и развиваться.</p>
        <Link className="back-home" to="/">← На главную</Link>
      </div>
      <form className="auth-card" onSubmit={handleSubmit}>
        <p className="eyebrow">DAYBOOK ACCOUNT</p>
        <h2>{copy.title}</h2>
        <p className="auth-subtitle">{copy.subtitle}</p>

        <label htmlFor="auth-email">Электронная почта</label>
        <input id="auth-email" type="email" autoComplete="email" value={email}
          onChange={(event) => setEmail(event.target.value)} required />

        {(mode === "register" || mode === "login" || mode === "reset-password") && <>
          <label htmlFor="auth-password">{mode === "reset-password" ? "Новый пароль" : "Пароль"}</label>
          <input id="auth-password" type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            minLength={mode === "login" ? 1 : 8} maxLength={128}
            value={password} onChange={(event) => setPassword(event.target.value)} required />
        </>}

        {mode === "register" && <>
          <label htmlFor="auth-confirm">Повтори пароль</label>
          <input id="auth-confirm" type="password" autoComplete="new-password"
            minLength={8} maxLength={128} value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)} required />
        </>}

        {mode === "reset-code" && <>
          <label htmlFor="auth-code">Шестизначный код</label>
          <input id="auth-code" inputMode="numeric" autoComplete="one-time-code"
            pattern="[0-9]{6}" maxLength={6} value={code}
            onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))} required />
        </>}

        {error && <p className="form-message error" role="alert">{error}</p>}
        {notice && <p className="form-message success" role="status">{notice}</p>}
        <button className="auth-submit" type="submit" disabled={busy}>
          {busy ? "Подожди…" : copy.action}
        </button>

        {mode === "register" && <p className="auth-switch">Уже есть аккаунт? <button type="button" onClick={() => changeMode("login")}>Войти</button></p>}
        {mode === "login" && <>
          <p className="auth-switch"><button type="button" onClick={() => changeMode("reset-email")}>Забыли пароль?</button></p>
          <p className="auth-switch">Ещё нет аккаунта? <button type="button" onClick={() => changeMode("register")}>Создать аккаунт</button></p>
        </>}
        {mode === "reset-email" && <p className="auth-switch"><button type="button" onClick={() => changeMode("login")}>Вернуться ко входу</button></p>}
        {mode === "reset-code" && <p className="auth-switch"><button type="button" onClick={() => changeMode("reset-email")}>Запросить новый код</button></p>}
        {mode === "reset-password" && <p className="auth-switch">Почта: {email}</p>}
      </form>
    </section>
  );
}
