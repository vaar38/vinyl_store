import { expect, test, type Page } from "@playwright/test";

const record = {
  id: 1,
  album: "Тестовый альбом",
  artist: "Тестовый исполнитель",
  price: "2990.00",
  available_stock: 1,
  cover_url: null,
};

async function mockStore(page: Page) {
  let quantity = 0;
  await page.route("**/api/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.slice(4);
    let body: unknown;
    let status = 200;
    if (path === "/records") {
      body = url.searchParams.get("q") === "нет" ? [] : [record];
    } else if (path === "/genres") {
      body = [{ id: 1, name: "Hip-hop", description: null }];
    } else if (path === "/records/1") {
      body = {
        ...record,
        description: "Описание альбома",
        release_year: 2013,
        genre: "Hip-hop",
      };
    } else if (path === "/auth/login") {
      body = { access_token: "test-token", token_type: "bearer" };
    } else if (path === "/users/me") {
      body = {
        id: 1,
        email: "test@example.com",
        full_name: "Покупатель",
        phone: null,
        role_code: "customer",
      };
    } else if (path === "/cart") {
      body = quantity
        ? [
            {
              record_id: 1,
              album: record.album,
              price: 2990,
              quantity,
              available_stock: 1,
              is_active: true,
            },
          ]
        : [];
    } else if (path === "/cart/items") {
      quantity += request.postDataJSON().quantity;
      body = { record_id: 1, quantity };
    } else if (path === "/cart/items/1") {
      quantity =
        request.method() === "DELETE" ? 0 : request.postDataJSON().quantity;
      if (!quantity) return route.fulfill({ status: 204 });
      body = { record_id: 1, quantity };
    } else if (path === "/orders") {
      quantity = 0;
      status = 201;
      body = { id: 42, status: "created", total_amount: 2990, delivery_fee: 0 };
    } else {
      status = 404;
      body = { detail: "Не найдено" };
    }
    await route.fulfill({
      status,
      contentType: "application/json",
      body: JSON.stringify(body),
    });
  });
}

test("каталог, карточка, поиск и мобильная ширина", async ({ page }) => {
  await mockStore(page);
  await page.goto("/");
  await page.getByRole("button", { name: record.album, exact: true }).click();
  await expect(
    page.getByRole("dialog").getByText("Описание альбома"),
  ).toBeVisible();
  await page.getByRole("button", { name: "Закрыть", exact: true }).click();
  await page.getByLabel("Поиск по альбому").fill("нет");
  await expect(
    page.getByRole("heading", { name: "Пока ничего не нашлось" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Сбросить фильтры" }).click();
  await expect(
    page.getByRole("button", { name: record.album, exact: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("вход, проверка количества и оформление", async ({ page }) => {
  await mockStore(page);
  await page.goto("/");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await page.getByLabel("Email", { exact: true }).fill("test@example.com");
  await page.getByLabel("Пароль", { exact: true }).fill("TestPassword123");
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Войти", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Аккаунт", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Добавить " + record.album + " в корзину" })
    .click();
  await expect(
    page.getByRole("status").filter({ hasText: "Пластинка добавлена" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Корзина/ }).click();
  await page.getByRole("button", { name: "Увеличить количество" }).click();
  await expect(
    page.getByRole("button", { name: "Оформить заказ" }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Уменьшить количество" }).click();
  await expect(
    page.getByRole("button", { name: "Оформить заказ" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Оформить заказ" }).click();
  await page.getByLabel("Телефон", { exact: true }).fill("+79990000000");
  await page.getByLabel("Адрес доставки").fill("Москва, Тестовая улица, 1");
  await page.getByRole("button", { name: "Подтвердить заказ" }).click();
  await expect(
    page.getByRole("heading", { name: "Заказ №42 оформлен" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Вернуться в магазин" }).click();
  await page.getByRole("button", { name: /Корзина/ }).click();
  await expect(page.getByText("Здесь будут ваши находки")).toBeVisible();
});

test("неверный пароль показывает ошибку входа", async ({ page }) => {
  await mockStore(page);
  await page.route("**/api/auth/login", route => route.fulfill({
    status: 401,
    contentType: "application/json",
    body: JSON.stringify({ detail: "Неверный email или пароль" }),
  }));
  await page.goto("/");
  await page.getByRole("button", { name: "Войти", exact: true }).click();
  await page.getByLabel("Email", { exact: true }).fill("admin@example.com");
  await page.getByLabel("Пароль", { exact: true }).fill("WrongPassword123");
  await page.getByRole("dialog").getByRole("button", { name: "Войти", exact: true }).click();
  await expect(page.getByRole("alert")).toHaveText("Неверный email или пароль");
});