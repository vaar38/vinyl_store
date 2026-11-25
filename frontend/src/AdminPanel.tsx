import { useEffect, useState, type FormEvent } from "react";
import { api, money } from "./api";

type Artist = {
  id: number;
  name: string;
  country_code: string | null;
  biography: string | null;
  image_url: string | null;
};
type Genre = { id: number; name: string; description: string | null };
type Product = {
  updated_at: string;
  id: number;
  album: string;
  artist_id: number;
  genre_id: number;
  price: number | string;
  available_stock: number;
  is_active: boolean;
  description: string | null;
  cover_url: string | null;
  release_year: number | null;
};
type Entity = Product | Artist | Genre;
type Tab = "records" | "artists" | "genres";

export default function AdminPanel({
  token,
  onChanged,
}: {
  token: string;
  onChanged: () => void;
}) {
  const [tab, setTab] = useState<Tab>("records");
  const [products, setProducts] = useState<Product[]>([]);
  const [artists, setArtists] = useState<Artist[]>([]);
  const [genres, setGenres] = useState<Genre[]>([]);
  const [editing, setEditing] = useState<Entity | "new" | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      api<Product[]>("/admin/records", {}, token),
      api<Artist[]>("/admin/artists", {}, token),
      api<Genre[]>("/admin/genres", {}, token),
    ])
      .then(([records, performers, styles]) => {
        if (active) {
          setProducts(records);
          setArtists(performers);
          setGenres(styles);
        }
      })
      .catch((cause) => {
        if (active) setError(cause.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [token, revision]);
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const form = new FormData(event.currentTarget);
    const value = (key: string) => String(form.get(key) || "").trim();
    const optional = (key: string) => value(key) || null;
    let body: object;
    if (tab === "records") {
      body = {
        ...(product ? { expected_updated_at: product.updated_at } : {}),
        album: value("album"),
        artist_id: Number(value("artist_id")),
        genre_id: Number(value("genre_id")),
        price: value("price"),
        available_stock: Number(value("available_stock")),
        is_active: form.has("is_active"),
        description: optional("description"),
        cover_url: optional("cover_url"),
        release_year: value("release_year")
          ? Number(value("release_year"))
          : null,
      };
    } else if (tab === "artists") {
      body = {
        name: value("name"),
        country_code: optional("country_code"),
        biography: optional("biography"),
        image_url: optional("image_url"),
      };
    } else body = { name: value("name"), description: optional("description") };
    try {
      const id = editing && editing !== "new" ? editing.id : null;
      await api(
        "/admin/" + tab + (id ? "/" + id : ""),
        {
          method: id ? "PUT" : "POST",
          body: JSON.stringify(body),
        },
        token,
      );
      setEditing(null);
      setRevision((current) => current + 1);
      onChanged();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function archive(product: Product) {
    if (!window.confirm("Скрыть пластинку из каталога?")) return;
    setBusy(true);
    setError("");
    try {
      await api("/admin/records/" + product.id, { method: "DELETE" }, token);
      setRevision((value) => value + 1);
      onChanged();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const product =
    editing && editing !== "new" && "album" in editing ? editing : null;
  const artist =
    editing && editing !== "new" && "biography" in editing ? editing : null;
  const genre =
    editing && editing !== "new" && "name" in editing ? editing : null;
  const entities: Entity[] =
    tab === "records" ? products : tab === "artists" ? artists : genres;
  return (
    <div className="admin-panel">
      <div className="tabs">
        {(
          [
            ["records", "Пластинки"],
            ["artists", "Исполнители"],
            ["genres", "Жанры"],
          ] as const
        ).map(([key, label]) => (
          <button
            disabled={busy}
            className={tab === key ? "active" : ""}
            key={key}
            onClick={() => {
              setTab(key);
              setEditing(null);
              setError("");
            }}
          >
            {label}
          </button>
        ))}
      </div>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {editing ? (
        <form
          className="form"
          onSubmit={save}
          key={tab + (editing === "new" ? "new" : editing.id)}
        >
          <h3>{editing === "new" ? "Добавить" : "Редактировать"}</h3>
          {tab === "records" ? (
            <>
              <label>
                Альбом
                <input
                  name="album"
                  required
                  maxLength={300}
                  defaultValue={product?.album}
                />
              </label>
              <div className="form-columns">
                <label>
                  Исполнитель
                  <select
                    aria-label="Исполнитель"
                    name="artist_id"
                    required
                    defaultValue={product?.artist_id || ""}
                  >
                    <option value="" disabled>
                      Выберите
                    </option>
                    {artists.map((artist) => (
                      <option key={artist.id} value={artist.id}>
                        {artist.name}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  Жанр
                  <select
                    aria-label="Жанр"
                    name="genre_id"
                    required
                    defaultValue={product?.genre_id || ""}
                  >
                    <option value="" disabled>
                      Выберите
                    </option>
                    {genres.map((genre) => (
                      <option key={genre.id} value={genre.id}>
                        {genre.name}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="form-columns">
                <label>
                  Цена, ₽
                  <input
                    name="price"
                    type="number"
                    min="0.01"
                    step="0.01"
                    max="9999999999.99"
                    required
                    defaultValue={product?.price}
                  />
                </label>
                <label>
                  Доступный остаток
                  <input
                    name="available_stock"
                    type="number"
                    min="0"
                    max="2147483647"
                    step="1"
                    required
                    defaultValue={product?.available_stock ?? 0}
                  />
                </label>
              </div>
              <label>
                Год выпуска
                <input
                  name="release_year"
                  type="number"
                  min="1900"
                  max="2100"
                  defaultValue={product?.release_year ?? ""}
                />
              </label>
              <label>
                URL обложки
                <input
                  type="url"
                  name="cover_url"
                  defaultValue={product?.cover_url || ""}
                />
              </label>
              <label>
                Описание
                <textarea
                  name="description"
                  defaultValue={product?.description || ""}
                />
              </label>
              <label className="checkbox">
                <input
                  name="is_active"
                  type="checkbox"
                  defaultChecked={product?.is_active ?? true}
                />
                Показывать в каталоге
              </label>
            </>
          ) : (
            <>
              <label>
                Название
                <input
                  name="name"
                  required
                  maxLength={200}
                  defaultValue={genre?.name || ""}
                />
              </label>
              {tab === "artists" ? (
                <>
                  <label>
                    Код страны
                    <input
                      name="country_code"
                      minLength={2}
                      maxLength={2}
                      placeholder="US"
                      defaultValue={artist?.country_code || ""}
                    />
                  </label>
                  <label>
                    URL изображения
                    <input
                      name="image_url"
                      type="url"
                      defaultValue={artist?.image_url || ""}
                    />
                  </label>
                  <label>
                    Биография
                    <textarea
                      name="biography"
                      defaultValue={artist?.biography || ""}
                    />
                  </label>
                </>
              ) : (
                <label>
                  Описание
                  <textarea
                    name="description"
                    defaultValue={(genre as Genre | null)?.description || ""}
                  />
                </label>
              )}
            </>
          )}
          <button
            className="primary full"
            disabled={
              busy || (tab === "records" && (!artists.length || !genres.length))
            }
          >
            {busy ? "Сохраняем…" : "Сохранить"}
          </button>
          <button
            className="text-button"
            type="button"
            disabled={busy}
            onClick={() => setEditing(null)}
          >
            Отмена
          </button>
        </form>
      ) : (
        <>
          <div className="management-toolbar">
            <button
              className="primary"
              disabled={busy || loading}
              onClick={() => {
                setEditing("new");
                setError("");
              }}
            >
              Добавить
            </button>
            <button
              className="secondary"
              disabled={loading || busy}
              onClick={() => setRevision((value) => value + 1)}
            >
              Обновить
            </button>
          </div>
          {loading ? (
            <p className="empty">Загрузка…</p>
          ) : entities.length === 0 ? (
            <p className="empty">Здесь пока пусто</p>
          ) : (
            entities.map((entity) => (
              <div className="admin-row" key={entity.id}>
                <div>
                  <strong>
                    {"album" in entity ? entity.album : entity.name}
                  </strong>
                  {"album" in entity && (
                    <p className="muted">
                      {money(entity.price)} · Остаток {entity.available_stock} ·{" "}
                      {entity.is_active ? "В каталоге" : "Скрыта"}
                    </p>
                  )}
                </div>
                <div>
                  <button
                    className="secondary"
                    disabled={busy}
                    onClick={() => {
                      setEditing(entity);
                      setError("");
                    }}
                  >
                    Изменить
                  </button>
                  {"album" in entity && entity.is_active && (
                    <button
                      className="text-button"
                      disabled={busy}
                      onClick={() => archive(entity)}
                    >
                      Скрыть
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </>
      )}
    </div>
  );
}
