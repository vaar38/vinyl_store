import OrdersPanel from "./OrdersPanel";
import AdminPanel from "./AdminPanel";
import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  ArrowDown,
  ArrowRight,
  Check,
  Disc3,
  LoaderCircle,
  Minus,
  Plus,
  Search,
  ShoppingBag,
  Trash2,
  UserRound,
  X,
} from "lucide-react";
import {
  api,
  ApiError,
  money,
  type CartItem,
  type Genre,
  type Order,
  type RecordDetail,
  type RecordItem,
  type User,
} from "./api";

type Panel =
  | "login"
  | "register"
  | "cart"
  | "checkout"
  | "account"
  | "orders"
  | "staff"
  | "admin"
  | null;

function Cover({
  record,
  large = false,
}: {
  record: RecordItem;
  large?: boolean;
}) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [record.cover_url]);
  return (
    <div className={`cover ${large ? "cover-large" : ""}`}>
      {record.cover_url && !failed ? (
        <img
          src={record.cover_url}
          alt={`Обложка ${record.album}`}
          onError={() => setFailed(true)}
        />
      ) : (
        <div className="record-art" aria-label="Обложка пока не добавлена">
          <div className="vinyl">
            <div className="vinyl-label">
              <Disc3 size={30} />
            </div>
          </div>
          <span>Обложка скоро появится</span>
        </div>
      )}
    </div>
  );
}

function CartCover({ item }: { item: CartItem }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [item.cover_url]);
  return (
    <div className="cart-disc">
      {item.cover_url && !failed ? (
        <img
          src={item.cover_url}
          alt={`Обложка ${item.album}`}
          onError={() => setFailed(true)}
        />
      ) : (
        <Disc3 size={32} aria-label="Обложка отсутствует" />
      )}
    </div>
  );
}

function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current!;
    element.showModal();
    return () => {
      element.close();
    };
  }, []);
  return (
    <dialog
      ref={dialog}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="dialog-head">
        <h2>{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="Закрыть">
          <X />
        </button>
      </div>
      {children}
    </dialog>
  );
}

export default function App() {
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [genres, setGenres] = useState<Genre[]>([]);
  const [genre, setGenre] = useState("");
  const [sort, setSort] = useState("default");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [catalogError, setCatalogError] = useState("");
  const [reload, setReload] = useState(0);
  const [token, setToken] = useState(
    () => sessionStorage.getItem("vinyl_token") || "",
  );
  const [user, setUser] = useState<User | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [cartLoaded, setCartLoaded] = useState(false);
  const [panel, setPanel] = useState<Panel>(null);
  const [detail, setDetail] = useState<RecordDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [order, setOrder] = useState<Order | null>(null);

  function logout() {
    sessionStorage.removeItem("vinyl_token");
    setToken("");
    setUser(null);
    setCart([]);
    setCartLoaded(false);
  }
  function showError(cause: unknown) {
    if (cause instanceof ApiError && cause.status === 401) {
      logout();
      setPanel("login");
      setError("Сессия истекла. Войдите снова.");
    } else
      setError(cause instanceof Error ? cause.message : "Произошла ошибка.");
  }
  function openPanel(next: Panel) {
    setError("");
    setPanel(next);
    setDetail(null);
    setOrder(null);
  }
  async function refreshCart(auth = token) {
    const items = await api<CartItem[]>("/cart", {}, auth);
    setCart(items);
    setCartLoaded(true);
  }

  useEffect(() => {
    let active = true;
    api<Genre[]>("/genres")
      .then((data) => {
        if (active) setGenres(data);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setCatalogError("");
    const timer = window.setTimeout(async () => {
      const params = new URLSearchParams();
      if (query.trim()) params.set("q", query.trim());
      if (genre) params.set("genre_id", genre);
      try {
        const data = await api<RecordItem[]>("/records?" + params);
        if (active) setRecords(data);
      } catch (cause) {
        if (active) setCatalogError((cause as Error).message);
      } finally {
        if (active) setLoading(false);
      }
    }, 250);
    return () => {
      active = false;
      window.clearTimeout(timer);
    };
  }, [query, genre, reload]);
  useEffect(() => {
    if (!token) return;
    let active = true;
    setCartLoaded(false);
    Promise.all([
      api<User>("/users/me", {}, token),
      api<CartItem[]>("/cart", {}, token),
    ])
      .then(([profile, items]) => {
        if (active) {
          setUser(profile);
          setCart(items);
          setCartLoaded(true);
        }
      })
      .catch((cause) => {
        if (active) showError(cause);
      });
    return () => {
      active = false;
    };
  }, [token]);
  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 3500);
    return () => window.clearTimeout(timer);
  }, [notice]);

  async function showDetail(id: number) {
    setError("");
    setDetailLoading(true);
    setPanel(null);
    try {
      setDetail(await api<RecordDetail>(`/records/${id}`));
    } catch (cause) {
      showError(cause);
    } finally {
      setDetailLoading(false);
    }
  }
  async function add(id: number) {
    if (!token) {
      openPanel("login");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await api(
        "/cart/items",
        {
          method: "POST",
          body: JSON.stringify({ record_id: id, quantity: 1 }),
        },
        token,
      );
      await refreshCart();
      setNotice("Пластинка добавлена в корзину");
    } catch (cause) {
      showError(cause);
    } finally {
      setBusy(false);
    }
  }
  async function changeItem(item: CartItem, quantity: number) {
    setBusy(true);
    setError("");
    try {
      await api(
        `/cart/items/${item.record_id}`,
        quantity === 0
          ? { method: "DELETE" }
          : { method: "PATCH", body: JSON.stringify({ quantity }) },
        token,
      );
      await refreshCart();
    } catch (cause) {
      showError(cause);
    } finally {
      setBusy(false);
    }
  }
  async function authenticate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    const credentials = {
      email: String(data.get("email")).trim(),
      password: String(data.get("password")),
    };
    try {
      if (panel === "register") {
        await api("/auth/register", {
          method: "POST",
          body: JSON.stringify({
            ...credentials,
            full_name: String(data.get("full_name")).trim(),
            phone: null,
          }),
        });
      }
      const result = await api<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify(credentials),
      });
      sessionStorage.setItem("vinyl_token", result.access_token);
      setToken(result.access_token);
      setPanel(null);
      setNotice("Вы вошли в аккаунт");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Не удалось войти.");
    } finally {
      setBusy(false);
    }
  }
  async function checkout(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const data = new FormData(event.currentTarget);
    try {
      const result = await api<Order>(
        "/orders",
        {
          method: "POST",
          body: JSON.stringify({
            recipient_name: String(data.get("recipient_name")).trim(),
            recipient_phone: String(data.get("recipient_phone")).trim(),
            delivery_address: String(data.get("delivery_address")).trim(),
            delivery_comment:
              String(data.get("delivery_comment")).trim() || null,
          }),
        },
        token,
      );
      setOrder(result);
      setCart([]);
      setPanel(null);
      setReload((value) => value + 1);
    } catch (cause) {
      showError(cause);
    } finally {
      setBusy(false);
    }
  }
  const sortedRecords = [...records].sort((a, b) => {
    if (sort === "price_asc") return Number(a.price) - Number(b.price) || a.id - b.id;
    if (sort === "price_desc") return Number(b.price) - Number(a.price) || a.id - b.id;
    if (sort === "album") return a.album.localeCompare(b.album, "ru") || a.id - b.id;
    return a.id - b.id;
  });

  const count = cart.reduce((sum, item) => sum + item.quantity, 0);
  const total = cart.reduce(
    (sum, item) => sum + Number(item.price) * item.quantity,
    0,
  );
  const unavailable = cart.some(
    (item) => !item.is_active || item.quantity > item.available_stock,
  );
  const close = () => {
    if (!busy) {
      setPanel(null);
      setDetail(null);
      setOrder(null);
      setError("");
    }
  };

  return (
    <>
      <header className="header">
        <a href="#" className="brand" aria-label="На главную">
          <Disc3 />
          <span>
            ВИНИЛ<span className="brand-dot">.</span>
          </span>
        </a>
        <nav>
          <a href="#catalog">Каталог</a>
        </nav>
        <div className="header-actions">
          <button
            className="account-button"
            aria-label={user ? "Аккаунт" : "Войти"}
            onClick={() => openPanel(user ? "account" : "login")}
          >
            <UserRound size={19} />
            <span>{user ? "Аккаунт" : "Войти"}</span>
          </button>
          <button
            className="bag-button"
            onClick={() => openPanel(token ? "cart" : "login")}
          >
            <ShoppingBag size={18} />
            <span>Корзина</span>
            <span className="count">{count}</span>
          </button>
        </div>
      </header>

      <main>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow">Магазин виниловых пластинок</p>
            <h1>
              Музыка,
              <br />
              которую
              <br />
              <em>можно держать.</em>
            </h1>
            <p className="hero-description">
              Новые пластинки для ваших любимых вечеров.
              <br />
              Выбирайте альбом, ставьте иглу, слушайте.
            </p>
            <a className="primary" href="#catalog">
              Найти свою пластинку <ArrowRight size={18} />
            </a>
          </div>
          <div className="hero-art">
            <img
              className="hero-record-photo"
              src="/images/asap-rocky-long-live-asap.jpg"
              alt="A$AP Rocky - LONG.LIVE.A$AP, vinyl edition"
              width="1200"
              height="1200"
              fetchPriority="high"
            />
          </div>
        </section>
        <div className="intro-strip">
          <span>
            <Disc3 size={18} /> Только новые пластинки
          </span>
          <span>Бережная упаковка</span>
          <span>Оплата при получении</span>
          <a href="#catalog" aria-label="Перейти к каталогу">
            <ArrowDown size={20} />
          </a>
        </div>

        <section className="catalog" id="catalog">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Ваша следующая находка</p>
              <h2>На нашей полке</h2>
            </div>
            <span className="muted">
              {loading ? "Загружаем…" : `${records.length} в каталоге`}
            </span>
          </div>
          <div className="filters">
            <label className="search">
              <Search size={19} />
              <input
                aria-label="Поиск по альбому"
                placeholder="Название альбома"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
              {query && (
                <button
                  onClick={() => setQuery("")}
                  aria-label="Очистить поиск"
                >
                  <X size={16} />
                </button>
              )}
            </label>
            <label className="genre-select">
              <span className="sr-only">Жанр</span>
              <select value={genre} onChange={(e) => setGenre(e.target.value)}>
                <option value="">Все жанры</option>
                {genres.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="genre-select sort-select">
              <span className="sr-only">Сортировка</span>
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                <option value="default">По умолчанию</option>
                <option value="price_asc">Сначала дешевле</option>
                <option value="price_desc">Сначала дороже</option>
                <option value="album">По названию</option>
              </select>
            </label>
          </div>
          {loading ? (
            <div className="empty">
              <LoaderCircle className="spin" /> Загружаем пластинки
            </div>
          ) : catalogError ? (
            <div className="empty" role="alert">
              <p>{catalogError}</p>
              <button
                className="secondary"
                onClick={() => setReload((value) => value + 1)}
              >
                Повторить
              </button>
            </div>
          ) : records.length === 0 ? (
            <div className="empty">
              <Disc3 size={38} />
              <h3>Пока ничего не нашлось</h3>
              <p>Попробуйте другое название или жанр.</p>
              <button
                className="secondary"
                onClick={() => {
                  setQuery("");
                  setGenre("");
                }}
              >
                Сбросить фильтры
              </button>
            </div>
          ) : (
            <div className="record-grid">
              {sortedRecords.map((record) => (
                <article className="record-card" key={record.id}>
                  <button
                    className="cover-button"
                    onClick={() => showDetail(record.id)}
                  >
                    <Cover record={record} />
                    <span className="cover-open">
                      Подробнее <ArrowRight size={17} />
                    </span>
                  </button>
                  <p className="artist">{record.artist}</p>
                  <button
                    className="album-title"
                    onClick={() => showDetail(record.id)}
                  >
                    {record.album}
                  </button>
                  <div className="card-bottom">
                    <div>
                      <strong>{money(record.price)}</strong>
                      <small>
                        {record.available_stock > 0
                          ? `В наличии · ${record.available_stock} шт.`
                          : "Нет в наличии"}
                      </small>
                    </div>
                    <button
                      disabled={busy || record.available_stock < 1}
                      className="add-button"
                      onClick={() => add(record.id)}
                      aria-label={`Добавить ${record.album} в корзину`}
                    >
                      <Plus size={23} />
                    </button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
      <footer>
        <a className="brand" href="#">
          <Disc3 size={24} />
          <span>ВИНИЛ.</span>
        </a>
        <span>Магазин виниловых пластинок</span>
        <a href="#catalog">Вернуться к музыке ↑</a>
      </footer>
      {notice && (
        <div className="toast" role="status">
          <Check size={18} />
          {notice}
        </div>
      )}
      {error && !panel && !detail && (
        <div className="global-error" role="alert">
          {error}
          <button onClick={() => setError("")} aria-label="Закрыть ошибку">
            <X size={18} />
          </button>
        </div>
      )}
      {detailLoading && (
        <div className="toast" role="status">
          <LoaderCircle className="spin" size={18} />
          Открываем карточку…
        </div>
      )}
      {detail && (
        <Modal title="Пластинка" onClose={close}>
          <div className="detail-layout">
            <Cover record={detail} large />
            <div>
              <p className="eyebrow">{detail.artist}</p>
              <h2>{detail.album}</h2>
              <p className="muted">
                {[detail.genre, detail.release_year]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
              {detail.description && (
                <p className="description">{detail.description}</p>
              )}
              <strong className="detail-price">{money(detail.price)}</strong>
              <p>
                {detail.available_stock
                  ? `В наличии: ${detail.available_stock} шт.`
                  : "Нет в наличии"}
              </p>
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <button
                className="primary full"
                disabled={busy || detail.available_stock < 1}
                onClick={() => add(detail.id)}
              >
                В корзину <ShoppingBag size={18} />
              </button>
            </div>
            {detail.artist_image_url && (
              <section className="artist-profile" aria-label="Об исполнителе">
                <img src={detail.artist_image_url} alt={detail.artist} />
                <div>
                  <p className="eyebrow">Исполнитель</p>
                  <h3>{detail.artist}</h3>
                  {detail.artist_biography && <p>{detail.artist_biography}</p>}
                </div>
              </section>
            )}
          </div>
        </Modal>
      )}
      {(panel === "login" || panel === "register") && (
        <Modal
          title={panel === "login" ? "Рады видеть вас" : "Создать аккаунт"}
          onClose={close}
        >
          <p className="muted">
            Сохраняйте находки в корзине и оформляйте доставку.
          </p>
          <form onSubmit={authenticate} className="form">
            {panel === "register" && (
              <label>
                Ваше имя
                <input
                  name="full_name"
                  autoComplete="name"
                  required
                  maxLength={200}
                />
              </label>
            )}
            <label>
              Email
              <input type="email" name="email" autoComplete="email" required />
            </label>
            <label>
              Пароль
              <input
                type="password"
                name="password"
                autoComplete={
                  panel === "register" ? "new-password" : "current-password"
                }
                minLength={panel === "register" ? 8 : undefined}
                maxLength={128}
                required
              />
            </label>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary full" disabled={busy}>
              {busy
                ? "Подождите…"
                : panel === "login"
                  ? "Войти"
                  : "Зарегистрироваться"}
              <ArrowRight size={18} />
            </button>
          </form>
          <button
            className="text-button"
            onClick={() => {
              setError("");
              setPanel(panel === "login" ? "register" : "login");
            }}
          >
            {panel === "login"
              ? "Ещё нет аккаунта? Зарегистрироваться"
              : "Уже есть аккаунт? Войти"}
          </button>
        </Modal>
      )}
      {panel === "account" && user && (
        <Modal title="Ваш аккаунт" onClose={close}>
          <p className="account-name">{user.full_name}</p>
          <p className="muted">{user.email}</p>
          {user.phone && <p>{user.phone}</p>}
          <div className="account-actions">
            <button
              className="secondary full"
              onClick={() => openPanel("orders")}
            >
              Мои заказы <ArrowRight size={18} />
            </button>
            {user.role_code && ["staff", "admin"].includes(user.role_code) && (
              <button
                className="secondary full"
                onClick={() => openPanel("staff")}
              >
                Рабочее место сотрудника
              </button>
            )}
            {user.role_code === "admin" && (
              <button
                className="secondary full"
                onClick={() => openPanel("admin")}
              >
                Управление каталогом
              </button>
            )}
          </div>
          <button className="secondary full" onClick={() => openPanel("cart")}>
            Открыть корзину <ShoppingBag size={18} />
          </button>
          <button
            className="text-button"
            onClick={() => {
              logout();
              setPanel(null);
            }}
          >
            Выйти из аккаунта
          </button>
        </Modal>
      )}
      {panel === "cart" && (
        <Modal title="Ваша корзина" onClose={close}>
          {!cartLoaded ? (
            <p className="empty">Загрузка корзины…</p>
          ) : cart.length === 0 ? (
            <div className="empty">
              <ShoppingBag size={35} />
              <h3>Здесь будут ваши находки</h3>
              <button className="primary" onClick={close}>
                Перейти к каталогу
              </button>
            </div>
          ) : (
            <>
              <div className="cart-items">
                {cart.map((item) => (
                  <div className="cart-item" key={item.record_id}>
                    <CartCover item={item} />
                    <div className="cart-info">
                      <h3>{item.album}</h3>
                      <p>{money(item.price)} / шт.</p>
                      {(!item.is_active ||
                        item.quantity > item.available_stock) && (
                        <small className="warning">
                          {!item.is_active
                            ? "Пластинка недоступна"
                            : `Доступно: ${item.available_stock} шт.`}
                        </small>
                      )}
                      <div className="quantity">
                        <button
                          disabled={busy || item.quantity <= 1}
                          onClick={() => changeItem(item, item.quantity - 1)}
                          aria-label="Уменьшить количество"
                        >
                          <Minus size={14} />
                        </button>
                        <span>{item.quantity}</span>
                        <button
                          disabled={busy || !item.is_active}
                          onClick={() => changeItem(item, item.quantity + 1)}
                          aria-label="Увеличить количество"
                        >
                          <Plus size={14} />
                        </button>
                      </div>
                    </div>
                    <div className="cart-right">
                      <strong>
                        {money(Number(item.price) * item.quantity)}
                      </strong>
                      <button
                        className="icon-button"
                        disabled={busy}
                        onClick={() => changeItem(item, 0)}
                        aria-label={`Удалить ${item.album}`}
                      >
                        <Trash2 size={17} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="total">
                <span>Итого</span>
                <strong>{money(total)}</strong>
              </div>
              <p className="muted">Доставка бесплатно · Оплата при получении</p>
              {unavailable && (
                <p className="error">
                  Уменьшите количество или удалите недоступные позиции.
                </p>
              )}
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              <button
                className="primary full"
                disabled={busy || unavailable}
                onClick={() => openPanel("checkout")}
              >
                Оформить заказ <ArrowRight size={18} />
              </button>
            </>
          )}
        </Modal>
      )}
      {panel === "checkout" && (
        <Modal title="Куда доставить пластинки?" onClose={close}>
          <form className="form" onSubmit={checkout}>
            <label>
              Имя получателя
              <input
                name="recipient_name"
                defaultValue={user?.full_name}
                autoComplete="name"
                maxLength={200}
                required
              />
            </label>
            <label>
              Телефон
              <input
                name="recipient_phone"
                type="tel"
                defaultValue={user?.phone || ""}
                autoComplete="tel"
                maxLength={32}
                placeholder="+7"
                required
              />
            </label>
            <label>
              Адрес доставки
              <textarea
                name="delivery_address"
                autoComplete="street-address"
                maxLength={500}
                required
              />
            </label>
            <label>
              Комментарий к доставке{" "}
              <span className="muted">(необязательно)</span>
              <textarea name="delivery_comment" maxLength={1000} />
            </label>
            <div className="total">
              <span>К оплате при получении</span>
              <strong>{money(total)}</strong>
            </div>
            <p className="muted">
              Доставка бесплатно. Остатки проверяются при оформлении.
            </p>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button className="primary full" disabled={busy}>
              {busy ? "Оформляем…" : "Подтвердить заказ"}
              <ArrowRight size={18} />
            </button>
            <button
              type="button"
              className="text-button"
              disabled={busy}
              onClick={() => openPanel("cart")}
            >
              Вернуться к корзине
            </button>
          </form>
        </Modal>
      )}
      {(panel === "orders" || panel === "staff") && (
        <Modal
          title={panel === "staff" ? "Заказы магазина" : "Мои заказы"}
          onClose={close}
        >
          <OrdersPanel
            token={token}
            staff={panel === "staff"}
            onChanged={() => setReload((value) => value + 1)}
          />
        </Modal>
      )}
      {panel === "admin" && (
        <Modal title="Управление каталогом" onClose={close}>
          <AdminPanel
            token={token}
            onChanged={() => setReload((value) => value + 1)}
          />
        </Modal>
      )}
      {order && (
        <Modal title={`Заказ №${order.id} оформлен`} onClose={close}>
          <div className="success">
            <span className="success-check">
              <Check size={36} />
            </span>
            <h3>Ваша музыка скоро будет ближе.</h3>
            <p>
              Пластинки зарезервированы. Следить за заказом можно в личном
              кабинете.
            </p>
            <div className="total">
              <span>К оплате при получении</span>
              <strong>{money(order.total_amount)}</strong>
            </div>
            <button className="primary full" onClick={close}>
              Вернуться в магазин <ArrowRight size={18} />
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
