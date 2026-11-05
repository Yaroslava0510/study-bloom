import { useState } from "react";
import { Link, Navigate, Route, Routes } from "react-router-dom";
import AuthPage from "./AuthPage";
import ProfilePage from "./ProfilePage";
import { apiBaseUrl } from "../shared/api/client";

const sections = [
  { path: "/", label: "Home", ru: "Главная" },
  { path: "/articles", label: "Articles", ru: "Статьи" },
  { path: "/study", label: "Study", ru: "Учёба" },
  { path: "/chats", label: "Chats", ru: "Чаты" },
  { path: "/profile", label: "Profile", ru: "Профиль" },
];

function Placeholder({ title, description }: { title: string; description: string }) {
  return <section className="page-card"><p className="eyebrow">DAYBOOK · WORKSPACE</p><h1>{title}</h1><p>{description}</p></section>;
}

export default function App() {
  const [english, setEnglish] = useState(false);
  const [apiStatus, setApiStatus] = useState<"idle" | "checking" | "online" | "offline">("idle");
  const text = (en: string, ru: string) => english ? en : ru;

  async function checkApi() {
    setApiStatus("checking");
    try {
      const response = await fetch(`${apiBaseUrl}/health`);
      if (!response.ok) throw new Error("API unavailable");
      setApiStatus("online");
    } catch {
      setApiStatus("offline");
    }
  }

  return (
    <div className="shell">
      <header className="topbar">
        <Link className="brand" to="/">DAYBOOK<span>✳</span></Link>
        <nav aria-label="Main navigation">
          {sections.map((item) => <Link key={item.path} to={item.path}>{english ? item.label : item.ru}</Link>)}
        </nav>
        <div className="top-actions">
          <Link className="account-link" to="/auth">{text("Account", "Аккаунт")}</Link>
          <button className="language" onClick={() => setEnglish(!english)}>{english ? "RU" : "EN"}</button>
        </div>
      </header>
      <main>
        <Routes>
          <Route path="/" element={<section className="hero">
            <p className="eyebrow">PEOPLE · IDEAS · STORIES · GROWTH</p>
            <h1>{text("Every day is a story.", "Каждый день — это история.")}</h1>
            <p className="lead">{text("A place to discover, create, connect and grow.", "Пространство, где можно узнавать новое, создавать, общаться и развиваться.")}</p>
            <div className="status-card">
              <div><strong>{text("Development workspace", "Среда разработки")}</strong><p>{text("The new DAYBOOK foundation is connected to the API.", "Новая основа DAYBOOK подготовлена для подключения к API.")}</p></div>
              <button onClick={checkApi} disabled={apiStatus === "checking"}>{apiStatus === "checking" ? text("Checking…", "Проверяем…") : text("Check API", "Проверить API")}</button>
              {apiStatus !== "idle" && <span className={apiStatus === "online" ? "online" : "offline"}>{apiStatus === "online" ? text("API online", "Сервер доступен") : apiStatus === "offline" ? text("API unavailable", "Сервер пока недоступен") : ""}</span>}
            </div>
            <Link className="hero-account" to="/auth">{text("Create your account", "Создать аккаунт")} ↗</Link>
          </section>} />
          <Route path="/auth" element={<AuthPage />} />
          <Route path="/articles" element={<Placeholder title={text("Articles", "Статьи")} description={text("Editorial and community stories will live here.", "Здесь будут редакционные и пользовательские статьи.")} />} />
          <Route path="/study" element={<Placeholder title={text("Study", "Учёба")} description={text("Goals, flexible planning, resources and your AI mentor.", "Цели, гибкое расписание, материалы и ИИ-наставник.")} />} />
          <Route path="/chats" element={<Placeholder title={text("Chats", "Чаты")} description={text("Conversations and communities, with privacy controls.", "Личные сообщения и сообщества с настройками приватности.")} />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer>DAYBOOK · Every day is a story.</footer>
    </div>
  );
}
