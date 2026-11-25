import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, LoaderCircle } from "lucide-react";
import { api, money } from "./api";

export const statusNames: Record<string, string> = {
  created: "Оформлен",
  assembling: "Собирается",
  ready: "Готов к отправке",
  shipped: "В доставке",
  delivered: "Доставлен",
  cancelled: "Отменён",
};
type OrderRow = {
  id: number;
  status: string;
  total_amount: number | string;
  delivery_fee: number | string;
  created_at: string;
  shipped_at: string | null;
  delivered_at: string | null;
};
type OrderDetails = OrderRow & {
  recipient_name: string;
  recipient_phone: string;
  delivery_address: string;
  delivery_comment: string | null;
  items: {
    record_id: number;
    album: string;
    artist: string;
    quantity: number;
    unit_price: number | string;
  }[];
  history: {
    previous_status: string | null;
    new_status: string;
    created_at: string;
  }[];
};
const date = (value: string) =>
  new Date(value).toLocaleString("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  });

export default function OrdersPanel({
  token,
  staff = false,
  onChanged,
}: {
  token: string;
  staff?: boolean;
  onChanged: () => void;
}) {
  const [orders, setOrders] = useState<OrderRow[]>([]);
  const [selected, setSelected] = useState<OrderDetails | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [revision, setRevision] = useState(0);
  const [filter, setFilter] = useState("");
  const base = staff ? "/staff/orders" : "/orders";
  useEffect(() => {
    let active = true;
    setLoading(true);
    api<OrderRow[]>(base, {}, token)
      .then((data) => {
        if (active) {
          setOrders(data);
          setError("");
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
  }, [base, token, revision]);
  async function open(id: number) {
    setBusy(true);
    setError("");
    try {
      setSelected(await api<OrderDetails>(base + "/" + id, {}, token));
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function change(status?: string) {
    if (!selected) return;
    if (
      !status &&
      !window.confirm("Отменить заказ? Пластинки вернутся в продажу.")
    )
      return;
    setBusy(true);
    setError("");
    try {
      await api(
        status
          ? base + "/" + selected.id + "/status"
          : base + "/" + selected.id + "/cancel",
        status
          ? { method: "PATCH", body: JSON.stringify({ status }) }
          : { method: "POST" },
        token,
      );
      setSelected(await api<OrderDetails>(base + "/" + selected.id, {}, token));
      setRevision((value) => value + 1);
      onChanged();
    } catch (cause) {
      setError((cause as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const transitions: Record<string, [string, string]> = {
    created: ["assembling", "Начать сборку"],
    assembling: ["ready", "Заказ собран"],
    ready: ["shipped", "Передать в доставку"],
    shipped: ["delivered", "Подтвердить вручение"],
  };
  return (
    <div className="orders-panel">
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {selected ? (
        <>
          <button
            className="text-button back-link"
            disabled={busy}
            onClick={() => setSelected(null)}
          >
            <ArrowLeft size={16} />К списку заказов
          </button>
          <div className="order-title">
            <h3>Заказ №{selected.id}</h3>
            <span className={"status status-" + selected.status}>
              {statusNames[selected.status] || selected.status}
            </span>
          </div>
          <p className="muted">{date(selected.created_at)}</p>
          <div className="order-address">
            <strong>{selected.recipient_name}</strong>
            <p>{selected.recipient_phone}</p>
            <p>{selected.delivery_address}</p>
            {selected.delivery_comment && <p>{selected.delivery_comment}</p>}
          </div>
          {selected.items.map((item) => (
            <div className="order-product" key={item.record_id}>
              <div>
                <strong>{item.album}</strong>
                <p className="muted">
                  {item.artist} · {item.quantity} шт. × {money(item.unit_price)}
                </p>
              </div>
              <span>{money(Number(item.unit_price) * item.quantity)}</span>
            </div>
          ))}
          <div className="total">
            <span>Итого с доставкой</span>
            <strong>{money(selected.total_amount)}</strong>
          </div>
          <p className="muted">
            Оплата при получении · Доставка {money(selected.delivery_fee)}
          </p>
          <ol className="timeline">
            {selected.history.map((event, index) => (
              <li key={index}>
                <strong>
                  {statusNames[event.new_status] || event.new_status}
                </strong>
                <span>{date(event.created_at)}</span>
              </li>
            ))}
          </ol>
          {staff && transitions[selected.status] && (
            <button
              className="primary full"
              disabled={busy}
              onClick={() => change(transitions[selected.status][0])}
            >
              {transitions[selected.status][1]}
              <ArrowRight size={17} />
            </button>
          )}
          {!staff &&
            ["created", "assembling", "ready"].includes(selected.status) && (
              <button
                className="secondary full"
                disabled={busy}
                onClick={() => change()}
              >
                Отменить заказ
              </button>
            )}
        </>
      ) : (
        <>
          <div className="management-toolbar">
            {staff && (
              <select
                aria-label="Статус заказа"
                value={filter}
                onChange={(e) => setFilter(e.target.value)}
              >
                <option value="">Все статусы</option>
                {Object.entries(statusNames).map(([key, value]) => (
                  <option key={key} value={key}>
                    {value}
                  </option>
                ))}
              </select>
            )}
            <button
              className="secondary"
              disabled={loading}
              onClick={() => setRevision((value) => value + 1)}
            >
              Обновить
            </button>
          </div>
          {loading ? (
            <p className="empty">
              <LoaderCircle className="spin" />
              Загрузка заказов
            </p>
          ) : orders.filter((order) => !filter || order.status === filter)
              .length === 0 ? (
            <p className="empty">Заказов пока нет</p>
          ) : (
            <div className="order-list">
              {orders
                .filter((order) => !filter || order.status === filter)
                .map((order) => (
                  <button
                    disabled={busy}
                    key={order.id}
                    className="order-row"
                    onClick={() => open(order.id)}
                  >
                    <div>
                      <strong>Заказ №{order.id}</strong>
                      <span>{date(order.created_at)}</span>
                    </div>
                    <span className={"status status-" + order.status}>
                      {statusNames[order.status] || order.status}
                    </span>
                    <strong>{money(order.total_amount)}</strong>
                    <ArrowRight size={17} />
                  </button>
                ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
