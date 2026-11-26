export type RecordItem = {
  id: number;
  album: string;
  artist: string;
  price: string | number;
  available_stock: number;
  cover_url: string | null;
};
export type RecordDetail = RecordItem & {
  artist_image_url?: string | null;
  artist_biography?: string | null;
  description: string | null;
  release_year: number | null;
  genre: string;
};
export type Genre = { id: number; name: string; description: string | null };
export type User = {
  role_code?: string;
  id: number;
  email: string;
  full_name: string;
  phone: string | null;
};
export type CartItem = {
  cover_url: string | null;
  record_id: number;
  album: string;
  price: number | string;
  quantity: number;
  available_stock: number;
  is_active: boolean;
};
export type Order = {
  id: number;
  status: string;
  total_amount: number | string;
  delivery_fee: number | string;
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch("/api" + path, { ...options, headers });
  } catch {
    throw new ApiError(
      0,
      "Не удалось связаться с магазином. Проверьте подключение и попробуйте ещё раз.",
    );
  }
  if (response.status === 204) return undefined as T;
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? "Проверьте заполненные поля."
          : "Не удалось выполнить запрос. Попробуйте ещё раз.";
    throw new ApiError(response.status, message);
  }
  return body as T;
}
export const money = (value: number | string) =>
  new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(Number(value));
