/* Простая точка запуска интерфейса, которую Nginx отдаёт браузеру напрямую. */
const root = document.querySelector("#root");

root.innerHTML = `
  <main style="max-width: 900px; margin: 4rem auto; padding: 0 1.5rem; font-family: system-ui, sans-serif">
    <h1>Платформа купли-продажи готового бизнеса</h1>
    <p>Сервисы доступны через защищённый API Gateway.</p>
    <p><a href="/api/search">Открыть каталог через API</a></p>
    <p>Создание объявления и личный кабинет подключаются на следующих этапах разработки.</p>
  </main>
`;
