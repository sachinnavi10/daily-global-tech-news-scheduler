const scheduleForm = document.querySelector("#schedule-form");
const scheduleSelect = document.querySelector("#schedule-select");
const scheduleStatus = document.querySelector("#schedule-status");
const searchForm = document.querySelector("#search-form");
const searchInput = document.querySelector("#search-input");
const categorySelect = document.querySelector("#category-select");
const newsList = document.querySelector("#news-list");
const newsStatus = document.querySelector("#news-status");
const briefingContent = document.querySelector("#briefing-content");
const briefingStatus = document.querySelector("#briefing-status");
const lastUpdated = document.querySelector("#last-updated");
const healthStatus = document.querySelector("#health-status");

const intervalMilliseconds = {
  "1_minute": 60 * 1000,
  "5_minutes": 5 * 60 * 1000,
  "1_hour": 60 * 60 * 1000,
  "1_day": 24 * 60 * 60 * 1000,
};
const refreshSettleDelay = 15 * 1000;

let currentSchedule = "daily";
let dailyTime = { hour: 6, minute: 0 };
let refreshTimer = null;

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  let payload;
  try {
    payload = await response.json();
  } catch {
    throw new Error("The application returned an invalid response.");
  }

  if (!response.ok) {
    throw new Error(payload.error || `Request failed (${response.status}).`);
  }
  return payload;
}

function createTextElement(tagName, className, text) {
  const element = document.createElement(tagName);
  if (className) {
    element.className = className;
  }
  element.textContent = text || "";
  return element;
}

function formatDate(value) {
  if (!value) {
    return "Publication date unavailable";
  }
  const parsedDate = new Date(value);
  return Number.isNaN(parsedDate.getTime())
    ? "Publication date unavailable"
    : parsedDate.toLocaleString();
}

function renderNews(articles) {
  newsList.replaceChildren();
  if (articles.length === 0) {
    newsList.append(createTextElement("p", "muted", "No matching news was found."));
    return;
  }

  for (const article of articles) {
    const card = createTextElement("article", "news-card", "");
    card.append(createTextElement("span", "category-tag", article.category));

    const title = document.createElement("a");
    title.textContent = article.title || "Untitled article";
    try {
      const articleUrl = new URL(article.url);
      if (articleUrl.protocol === "https:" || articleUrl.protocol === "http:") {
        title.href = articleUrl.href;
        title.target = "_blank";
        title.rel = "noopener noreferrer";
      }
    } catch {
      title.removeAttribute("href");
    }

    const titleHeading = document.createElement("h3");
    titleHeading.append(title);
    card.append(titleHeading);
    card.append(
      createTextElement(
        "p",
        "",
        article.description || "The source did not provide a description.",
      ),
    );
    card.append(
      createTextElement(
        "p",
        "muted",
        `${article.source || "Unknown"} · ${formatDate(article.published_at)}`,
      ),
    );
    newsList.append(card);
  }
}

async function loadNews() {
  const keyword = searchInput.value.trim();
  const category = categorySelect.value;
  let url = "/news?limit=50";
  if (keyword) {
    url = `/news/search?keyword=${encodeURIComponent(keyword)}&limit=50`;
  } else if (category) {
    url = `/news/category/${encodeURIComponent(category)}?limit=50`;
  }

  try {
    const result = await requestJson(url);
    renderNews(result.news || []);
    newsStatus.textContent = "";
  } catch (error) {
    newsStatus.textContent = error.message;
  }
}

function renderBriefing(briefing) {
  briefingContent.replaceChildren();
  const sections = document.createElement("div");
  sections.className = "briefing-sections";

  for (const [sectionName, stories] of Object.entries(briefing.categories || {})) {
    const section = createTextElement("section", "briefing-section", "");
    section.append(createTextElement("h3", "", sectionName));
    if (stories.length === 0) {
      section.append(createTextElement("p", "muted", "No major stories found."));
    }

    for (const story of stories) {
      const storyCard = createTextElement("article", "briefing-story", "");
      storyCard.append(createTextElement("h4", "", story.title));
      storyCard.append(createTextElement("p", "", story.summary));
      storyCard.append(
        createTextElement("p", "muted", `Why it matters: ${story.why_it_matters}`),
      );
      storyCard.append(createTextElement("p", "muted", `Source: ${story.source}`));
      section.append(storyCard);
    }
    sections.append(section);
  }

  briefingContent.append(sections);
  const extra = createTextElement("div", "briefing-extra", "");
  extra.append(createTextElement("h3", "", "Learning of the day"));
  extra.append(createTextElement("p", "", briefing.learning_of_the_day));
  extra.append(createTextElement("h3", "", "Career opportunity"));
  extra.append(createTextElement("p", "", briefing.career_opportunity));
  briefingContent.append(extra);
  lastUpdated.textContent = `Last generated: ${formatDate(briefing.generated_at)}`;
}

async function loadBriefing() {
  try {
    const result = await requestJson("/briefings?limit=1");
    const briefing = result.briefings && result.briefings[0];
    if (!briefing) {
      briefingContent.replaceChildren();
      briefingStatus.textContent = "The first briefing will appear after a news refresh.";
      lastUpdated.textContent = "Waiting for the first briefing…";
      return;
    }
    briefingStatus.textContent = "";
    renderBriefing(briefing);
  } catch (error) {
    briefingStatus.textContent = error.message;
  }
}

async function loadHealth() {
  try {
    const result = await requestJson("/health");
    healthStatus.textContent = `Application: ${result.status}; database: ${result.database}.`;
  } catch (error) {
    healthStatus.textContent = error.message;
  }
}

function millisecondsUntilDailyRun() {
  const now = new Date();
  const nextRun = new Date(now);
  nextRun.setHours(dailyTime.hour, dailyTime.minute, 0, 0);
  if (nextRun <= now) {
    nextRun.setDate(nextRun.getDate() + 1);
  }
  return nextRun.getTime() - now.getTime();
}

function scheduleDisplayRefresh() {
  window.clearTimeout(refreshTimer);
  const delay =
    currentSchedule === "daily"
      ? millisecondsUntilDailyRun()
      : intervalMilliseconds[currentSchedule];

  refreshTimer = window.setTimeout(async () => {
    await new Promise((resolve) => window.setTimeout(resolve, refreshSettleDelay));
    await Promise.all([loadNews(), loadBriefing(), loadHealth()]);
    scheduleDisplayRefresh();
  }, delay);
}

async function loadSchedule() {
  try {
    const result = await requestJson("/settings/schedule");
    currentSchedule = result.current.value;
    dailyTime = result.daily_time;
    scheduleSelect.replaceChildren();

    const optionOrder = ["1_minute", "5_minutes", "1_hour", "1_day", "daily"];
    for (const value of optionOrder) {
      const label = result.available[value];
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      scheduleSelect.append(option);
    }
    scheduleSelect.value = currentSchedule;
    scheduleStatus.textContent = `Current setting: ${result.current.label}.`;
    scheduleDisplayRefresh();
  } catch (error) {
    scheduleStatus.textContent = error.message;
    scheduleSelect.disabled = true;
  }
}

scheduleForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  scheduleStatus.textContent = "Saving schedule and starting a refresh…";
  try {
    const result = await requestJson("/settings/schedule", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ schedule: scheduleSelect.value }),
    });
    currentSchedule = result.current.value;
    scheduleStatus.textContent = `Current setting: ${result.current.label}.`;
    scheduleStatus.textContent += " The news refresh has started.";
    scheduleDisplayRefresh();
    await new Promise((resolve) => window.setTimeout(resolve, refreshSettleDelay));
    await Promise.all([loadNews(), loadBriefing(), loadHealth()]);
  } catch (error) {
    scheduleStatus.textContent = error.message;
  }
});

searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  loadNews();
});

categorySelect.addEventListener("change", loadNews);

async function startPage() {
  await loadSchedule();
  await Promise.all([loadNews(), loadBriefing(), loadHealth()]);
  window.setTimeout(
    () => Promise.all([loadNews(), loadBriefing(), loadHealth()]),
    refreshSettleDelay,
  );
}

startPage();
