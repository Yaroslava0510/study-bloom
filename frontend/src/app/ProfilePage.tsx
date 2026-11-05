import { FormEvent, useEffect, useState } from "react";
import { apiGet, apiPatch } from "../shared/api/client";

type Profile = {
  display_name: string;
  email: string;
  bio: string;
  birthday: string | null;
  interests: string[];
  theme: "cloud" | "blue" | "lavender" | "sage" | "rose";
  timezone: string;
};

const themeLabels: Record<Profile["theme"], string> = {
  cloud: "Облачный",
  blue: "Нежно-голубой",
  lavender: "Лавандовый",
  sage: "Шалфейный",
  rose: "Пудрово-розовый",
};

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [interests, setInterests] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    apiGet<Profile>("/api/v1/profile/me")
      .then((data) => {
        setProfile(data);
        setInterests(data.interests.join(", "));
      })
      .catch(() => setMessage("Не удалось загрузить профиль. Войди в аккаунт и попробуй снова."))
      .finally(() => setLoading(false));
  }, []);

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    setMessage("");
    try {
      const updated = await apiPatch<Profile>("/api/v1/profile/me", {
        display_name: profile.display_name,
        bio: profile.bio,
        birthday: profile.birthday || null,
        interests: interests.split(",").map((item) => item.trim()).filter(Boolean),
        theme: profile.theme,
        timezone: profile.timezone,
      });
      setProfile(updated);
      setInterests(updated.interests.join(", "));
      setMessage("Изменения сохранены.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Не удалось сохранить изменения.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <section className="page-card"><p>Загружаем профиль…</p></section>;
  if (!profile) return <section className="page-card"><p>{message}</p><a href="/auth">Перейти ко входу →</a></section>;

  return (
    <section className="profile-layout">
      <div className="profile-heading">
        <p className="eyebrow">DAYBOOK · YOUR SPACE</p>
        <h1>Твой профиль</h1>
        <p>Настрой страницу так, чтобы она отражала тебя и твои интересы.</p>
      </div>
      <form className="profile-card" onSubmit={saveProfile}>
        <div className="profile-avatar" aria-hidden="true">{profile.display_name.trim().charAt(0).toUpperCase() || "D"}</div>
        <p className="profile-email">{profile.email}</p>
        <label htmlFor="display-name">Имя</label>
        <input id="display-name" required maxLength={120} value={profile.display_name}
          onChange={(event) => setProfile({ ...profile, display_name: event.target.value })} />
        <label htmlFor="bio">О себе</label>
        <textarea id="bio" maxLength={300} rows={3} placeholder="Несколько слов о том, что тебе интересно…"
          value={profile.bio} onChange={(event) => setProfile({ ...profile, bio: event.target.value })} />
        <label htmlFor="birthday">Дата рождения</label>
        <input id="birthday" type="date" value={profile.birthday || ""}
          onChange={(event) => setProfile({ ...profile, birthday: event.target.value || null })} />
        <label htmlFor="interests">Интересы</label>
        <input id="interests" placeholder="Наука, книги, история…" value={interests}
          onChange={(event) => setInterests(event.target.value)} />
        <p className="field-hint">Разделяй интересы запятыми.</p>
        <label htmlFor="theme">Цветовая тема</label>
        <select id="theme" value={profile.theme}
          onChange={(event) => setProfile({ ...profile, theme: event.target.value as Profile["theme"] })}>
          {Object.entries(themeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <label htmlFor="timezone">Часовой пояс</label>
        <input id="timezone" maxLength={64} value={profile.timezone}
          onChange={(event) => setProfile({ ...profile, timezone: event.target.value })} />
        <button className="profile-save" type="submit" disabled={saving}>{saving ? "Сохраняем…" : "Сохранить изменения"}</button>
        {message && <p className="form-message success" role="status">{message}</p>}
      </form>
    </section>
  );
}
