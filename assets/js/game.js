const STORAGE_KEY = "space-colony-save-v2";
const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || "";
const backendEnabled = Boolean(csrfToken) && window.location.protocol !== "file:";

const upgradeConfig = {
  click: {
    label: "Harvest Enhancer",
    resourceLabel: "click power",
    paysWith: "mixed",
    baseCost: 60,
    costGrowth: 2.0,
    baseRate: 0,
    icon: "🦾"
  },
  oxygen: {
    label: "Oxygen Extractor",
    resourceLabel: "oxygen",
    paysWith: "minerals",
    baseCost: 120,
    costGrowth: 2.0,
    baseRate: 2.0,
    icon: "💨"
  },
  water: {
    label: "Water Extractor",
    resourceLabel: "water",
    paysWith: "oxygen",
    baseCost: 120,
    costGrowth: 2.0,
    baseRate: 2.0,
    icon: "💧"
  },
  minerals: {
    label: "Mining Drill",
    resourceLabel: "minerals",
    paysWith: "water",
    baseCost: 120,
    costGrowth: 2.0,
    baseRate: 2.0,
    icon: "💎"
  }
};

const milestones = [
  { target: 250, reward: 20, text: "Collect 250 total resources to expand the first dome." },
  { target: 650, reward: 45, text: "Reach 650 total resources to build a second oxygen farm." },
  { target: 1400, reward: 90, text: "Reach 1,400 total resources to launch the orbital beacon." },
  { target: 3000, reward: 160, text: "Reach 3,000 total resources to unlock a deep-core survey." },
  { target: 7000, reward: 300, text: "Reach 7,000 total resources to become a frontier megacolony." }
];

const achievementConfig = [
  { id: "first-harvest", icon: "✨", name: "First Harvest", test: (save) => save.totalClicks >= 1 },
  { id: "combo-10", icon: "🔥", name: "Hot Streak", test: (save) => save.bestCombo >= 10 },
  { id: "score-1000", icon: "⭐", name: "Rising Colony", test: (save) => save.score >= 1000 },
  { id: "builder-5", icon: "🏗️", name: "Builder", test: (save) => getTotalOwned(save) >= 5 },
  { id: "autos-10", icon: "⚙️", name: "Automation Age", test: (save) => getTotalRate(save) >= 10 },
  { id: "deep-space", icon: "🏆", name: "Deep Space", test: (save) => save.milestoneIndex >= 3 }
];

const newsPool = [
  "Colony news: miners request shinier drills.",
  "Colony news: oxygen farm reports suspiciously fresh air.",
  "Colony news: command says one more upgrade cannot hurt.",
  "Colony news: scanner found a glowing comet nearby.",
  "Colony news: engineers believe bigger numbers are better.",
  "Colony news: auto-extractors continue working while you plan."
];

const defaultState = {
  resources: {
    oxygen: 50,
    water: 50,
    minerals: 50
  },
  upgrades: {
    oxygen: 0,
    water: 0,
    minerals: 0,
    click: 0
  },
  totalCollected: 0,
  totalClicks: 0,
  score: 0,
  bestCombo: 1,
  milestoneIndex: 0,
  achievements: [],
  bonusMultiplier: 1,
  bonusUntil: 0,
  lastSaved: Date.now()
};

const stage = document.getElementById("planetStage");
const astronaut = document.getElementById("astronaut");
const digEffect = document.getElementById("digEffect");
const comboBanner = document.getElementById("comboBanner");
const eventLog = document.getElementById("eventLog");
const colonyCore = document.getElementById("colonyCore");
const cosmicBonus = document.getElementById("cosmicBonus");
const newsTicker = document.getElementById("newsTicker");
const achievementList = document.getElementById("achievementList");

const oxygenCount = document.getElementById("oxygenCount");
const waterCount = document.getElementById("waterCount");
const mineralCount = document.getElementById("mineralCount");
const scoreCount = document.getElementById("scoreCount");
const stageScore = document.getElementById("stageScore");
const comboCount = document.getElementById("comboCount");
const clickPowerCount = document.getElementById("clickPowerCount");
const corePower = document.getElementById("corePower");
const rateCount = document.getElementById("rateCount");
const missionText = document.getElementById("missionText");
const missionFill = document.getElementById("missionFill");
const missionReward = document.getElementById("missionReward");
const nodePositions = {
  oxygen: { left: "24%", bottom: "132px" },
  water: { left: "68%", bottom: "118px" },
  minerals: { left: "82%", bottom: "140px" }
};

let state = loadState();
let isCollecting = false;
let collectTimer = null;
let combo = 1;
let lastClickTime = 0;
let lastMove = 0;
let autosaveTimer = null;
let pendingCollectRequests = 0;

function cloneDefaultState() {
  return JSON.parse(JSON.stringify(defaultState));
}

function loadState() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (!saved) return cloneDefaultState();

    return {
      ...cloneDefaultState(),
      ...saved,
      resources: { ...defaultState.resources, ...saved.resources },
      upgrades: { ...defaultState.upgrades, ...saved.upgrades },
      achievements: saved.achievements || []
    };
  } catch (error) {
    return cloneDefaultState();
  }
}

function saveState() {
  if (backendEnabled) return;
  state.lastSaved = Date.now();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

async function apiRequest(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
      ...(options.headers || {})
    }
  });

  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }

  return data;
}

function applyServerPayload(payload) {
  if (!payload?.resources) return;

  state.resources.oxygen = payload.resources.oxygen;
  state.resources.water = payload.resources.water;
  state.resources.minerals = payload.resources.minerals;
  state.score = payload.resources.score;
  state.totalCollected = payload.resources.total_collected;
  state.bestCombo = Math.max(state.bestCombo, payload.resources.best_combo || 1);
  state.upgrades = {
    ...state.upgrades,
    ...(payload.upgrades || {})
  };
}

async function hydrateFromServer() {
  if (!backendEnabled) return;

  try {
    const payload = await apiRequest("/api/colony-state");
    applyServerPayload(payload);
    updateDisplay();
  } catch (error) {
    addEvent(`⚠️ Could not load saved colony state: ${error.message}`);
  }
}

async function syncCollection(resource, amount, bestCombo, comboValue, criticalHit) {
  if (!backendEnabled) return;

  pendingCollectRequests += 1;
  try {
    const payload = await apiRequest("/api/collect", {
      method: "POST",
      body: JSON.stringify({
        resource,
        amount,
        best_combo: bestCombo,
        combo: comboValue,
        critical: criticalHit
      })
    });
    applyServerPayload(payload);
    updateDisplay();
  } catch (error) {
    addEvent(`⚠️ Collection sync failed: ${error.message}`);
  } finally {
    pendingCollectRequests -= 1;
  }
}

function formatNumber(value) {
  const numeric = Number(value);
  if (Number.isNaN(numeric)) return "0";
  const rounded = Number(numeric.toFixed(1));
  if (Number.isInteger(rounded)) {
    return rounded.toLocaleString();
  }
  return rounded.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
}

function getUpgradeCost(type) {
  const config = upgradeConfig[type];
  return Math.floor(config.baseCost * Math.pow(config.costGrowth, state.upgrades[type]));
}

function getResourceRate(type, save = state) {
  if (type === "click") return 0;
  const config = upgradeConfig[type];
  const level = save.upgrades[type];
  if (level <= 0) return 0;
  return config.baseRate + 0.6 * Math.max(0, level - 1);
}

function getTotalRate(save = state) {
  return Object.keys(upgradeConfig).reduce((total, type) => {
    if (type === "click") return total;
    return total + getResourceRate(type, save);
  }, 0);
}

function getTotalOwned(save = state) {
  return (save.upgrades.oxygen || 0) + (save.upgrades.water || 0) + (save.upgrades.minerals || 0);
}

function getClickPower() {
  const clickLevel = state.upgrades.click || 0;
  const clickBonus = Math.floor(clickLevel / 2) * 0.5 + (clickLevel % 2 === 1 ? 0.2 : 0);
  const buildingBonus = Math.floor(getTotalOwned() / 3);
  const achievementBonus = Math.floor(state.achievements.length / 2);
  return 1 + clickBonus + buildingBonus + achievementBonus;
}

function getActiveMultiplier() {
  return Date.now() < state.bonusUntil ? state.bonusMultiplier : 1;
}

function getCurrentMilestone() {
  if (state.milestoneIndex >= milestones.length) return null;
  return milestones[state.milestoneIndex];
}

function randomResource() {
  const keys = ["oxygen", "water", "minerals"];
  const weights = keys.map((key) => 1 + state.upgrades[key] * 0.15);
  const total = weights.reduce((sum, value) => sum + value, 0);
  let roll = Math.random() * total;

  for (let index = 0; index < keys.length; index += 1) {
    roll -= weights[index];
    if (roll <= 0) return keys[index];
  }

  return keys[0];
}

function updateDisplay() {
  if (oxygenCount) oxygenCount.textContent = formatNumber(state.resources.oxygen);
  if (waterCount) waterCount.textContent = formatNumber(state.resources.water);
  if (mineralCount) mineralCount.textContent = formatNumber(state.resources.minerals);
  if (scoreCount) scoreCount.textContent = formatNumber(state.score);
  if (stageScore) stageScore.textContent = formatNumber(state.score);
  if (comboCount) comboCount.textContent = `x${combo}`;
  if (clickPowerCount) clickPowerCount.textContent = `+${getClickPower()}`;
  if (corePower) corePower.textContent = `+${getClickPower()}`;
  if (rateCount) rateCount.textContent = `${(getTotalRate() * getActiveMultiplier()).toFixed(1)} / sec`;

  if (astronaut) {
    if (getTotalRate() > 0) {
      astronaut.classList.add('walking');
    } else {
      astronaut.classList.remove('walking');
    }
  }

  updateStatusBars();
  updateMission();
  updateUpgradeButtons();
  checkAchievements();
  updateAchievementList();
}

function updateStatusBars() {
  const oxygenStatus = document.getElementById("oxygenStatus");
  const waterStatus = document.getElementById("waterStatus");
  const powerStatus = document.getElementById("powerStatus");
  const fills = document.querySelectorAll(".left-hud .fill");
  const oxygenPercent = Math.min(100, Math.floor(35 + state.resources.oxygen / 12));
  const waterPercent = Math.min(100, Math.floor(30 + state.resources.water / 12));
  const powerPercent = Math.min(100, Math.floor(25 + getTotalRate() * 8 + state.score / 300));

  if (oxygenStatus) oxygenStatus.textContent = `${oxygenPercent}%`;
  if (waterStatus) waterStatus.textContent = `${waterPercent}%`;
  if (powerStatus) powerStatus.textContent = `${powerPercent}%`;
  if (fills[0]) fills[0].style.width = `${oxygenPercent}%`;
  if (fills[1]) fills[1].style.width = `${waterPercent}%`;
  if (fills[2]) fills[2].style.width = `${powerPercent}%`;
}

function updateMission() {
  const milestone = getCurrentMilestone();
  if (!milestone) {
    if (missionText) missionText.textContent = "Megacolony online. Keep upgrading to chase a higher score.";
    if (missionFill) missionFill.style.width = "100%";
    if (missionReward) missionReward.textContent = "All milestones complete";
    return;
  }

  const previousTarget = milestones[state.milestoneIndex - 1]?.target || 0;
  const currentProgress = Math.max(0, state.totalCollected - previousTarget);
  const needed = milestone.target - previousTarget;
  const percent = Math.min(100, (currentProgress / needed) * 100);

  if (missionText) missionText.textContent = milestone.text;
  if (missionFill) missionFill.style.width = `${percent}%`;
  if (missionReward) missionReward.textContent = `Reward: +${milestone.reward} of every resource`;

  if (state.totalCollected >= milestone.target) {
    state.resources.oxygen += milestone.reward;
    state.resources.water += milestone.reward;
    state.resources.minerals += milestone.reward;
    state.score += milestone.reward * 8;
    state.milestoneIndex += 1;
    addEvent(`🏆 Milestone reached. Colony gained +${milestone.reward} of every resource.`);
    saveState();
    updateDisplay();
  }
}

function updateUpgradeButtons() {
  Object.keys(upgradeConfig).forEach((type) => {
    const config = upgradeConfig[type];
    const level = state.upgrades[type];
    const cost = getUpgradeCost(type);
    const buttons = document.querySelectorAll(`[data-upgrade="${type}"]`);
    const dashboardLevel = document.getElementById(`${type}Level`);
    const dashboardRate = document.getElementById(`${type}RateText`);
    const pageLevel = document.getElementById(`${type}UpgradeLevel`);
    const pageRate = document.getElementById(`${type}UpgradeRate`);
    let canBuy = false;

    if (config.paysWith === "mixed") {
      const perResource = Math.floor(cost / 3);
      canBuy = state.resources.oxygen >= perResource && state.resources.water >= perResource && state.resources.minerals >= perResource;
    } else {
      canBuy = state.resources[config.paysWith] >= cost;
    }

    buttons.forEach((button) => {
      if (config.paysWith === "mixed") {
        const perResource = Math.floor(cost / 3);
        button.textContent = `Buy ${level + 1}: ${formatNumber(perResource)} each`;
      } else {
        button.textContent = `Buy ${level + 1}: ${formatNumber(cost)} ${config.paysWith}`;
      }
      button.disabled = !canBuy;
      button.classList.toggle("ready", canBuy);
    });

    if (dashboardLevel) dashboardLevel.textContent = `Owned ${level}`;
    if (dashboardRate) {
      dashboardRate.textContent = type === "click" ? `+${getClickPower().toFixed(1)} / click` : `+${getResourceRate(type).toFixed(1)} / sec`;
    }
    if (pageLevel) pageLevel.textContent = `Level ${level}`;
    if (pageRate) {
      pageRate.textContent = type === "click" ? `+${getClickPower().toFixed(1)} per click` : `+${getResourceRate(type).toFixed(1)} ${config.resourceLabel} / sec`;
    }
  });
}

function updateAchievementList() {
  if (!achievementList) return;
  achievementList.innerHTML = achievementConfig.map((achievement) => {
    const unlocked = state.achievements.includes(achievement.id);
    return `<span class="achievement-badge ${unlocked ? "unlocked" : "locked"}" title="${achievement.name}">${achievement.icon}<strong>${achievement.name}</strong></span>`;
  }).join("");
}

function checkAchievements() {
  achievementConfig.forEach((achievement) => {
    if (!state.achievements.includes(achievement.id) && achievement.test(state)) {
      state.achievements.push(achievement.id);
      addEvent(`${achievement.icon} Achievement unlocked: ${achievement.name}.`);
      showToast(`${achievement.icon} ${achievement.name}`);
      saveState();
    }
  });
}

function moveAstronaut(event) {
  if (!stage || !astronaut) return;
  const rect = stage.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const percent = Math.max(8, Math.min(88, (x / rect.width) * 100));
  astronaut.style.left = `${percent}%`;
}

function collectResource(event) {
  if (!stage || !astronaut) return;
  moveAstronaut(event);

  const now = Date.now();
  combo = now - lastClickTime < 700 ? Math.min(combo + 1, 25) : 1;
  lastClickTime = now;

  const gained = randomResource();
  const critical = Math.random() < Math.min(0.08 + combo * 0.006, 0.22);
  const multiplier = getActiveMultiplier();
  const baseAmount = getClickPower() + Math.floor(combo / 8);
  const targetAmount = (critical ? baseAmount + 2 + Math.floor(combo / 6) : baseAmount) * multiplier;
  const amount = resolveClickAmount(targetAmount);
  const scoreGain = amount * combo * (critical ? 4 : 2);

  state.resources[gained] += amount;
  state.totalCollected += amount;
  state.totalClicks += 1;
  state.score += scoreGain;
  state.bestCombo = Math.max(state.bestCombo, combo);

  showGain(`+${formatNumber(amount)} ${gained}${critical ? "!" : ""}`, gained, event);
  showCombo();
  updateDisplay();
  syncCollection(gained, amount, state.bestCombo, combo, critical);
}

function resolveClickAmount(power) {
  const base = Math.floor(power);
  const remainder = power - base;
  return base + (Math.random() < remainder ? 1 : 0);
}

function showGain(text, type, event) {
  if (!digEffect || !stage) return;
  digEffect.textContent = text;
  digEffect.dataset.type = type;
  digEffect.style.left = astronaut?.style.left || "50%";
  digEffect.classList.remove("show");
  void digEffect.offsetWidth;
  digEffect.classList.add("show");
  spawnSpark(event);
}

function showCombo() {
  if (!comboBanner) return;
  const multiplier = getActiveMultiplier();
  comboBanner.textContent = multiplier > 1 ? `Frenzy x${multiplier}` : combo >= 5 ? `Combo x${combo}` : "Keep clicking";
  comboBanner.classList.toggle("hot", combo >= 10);
  comboBanner.classList.remove("pop");
  void comboBanner.offsetWidth;
  comboBanner.classList.add("pop");
}

function showToast(message) {
  if (!stage) return;
  const toast = document.createElement("div");
  toast.className = "reward-toast";
  toast.textContent = message;
  stage.appendChild(toast);
  toast.addEventListener("animationend", () => toast.remove());
}

function spawnSpark(event) {
  if (!stage || !event) return;
  const rect = stage.getBoundingClientRect();
  const spark = document.createElement("span");
  spark.className = "click-spark";
  spark.style.left = `${event.clientX - rect.left}px`;
  spark.style.top = `${event.clientY - rect.top}px`;
  stage.appendChild(spark);
  spark.addEventListener("animationend", () => spark.remove());
}

function startCollecting(event) {
  if (isCollecting) return;
  isCollecting = true;
  astronaut?.classList.add("mining");
  collectResource(event);

  collectTimer = setInterval(() => {
    if (!isCollecting || !stage || !astronaut) return;
    const left = parseFloat(astronaut.style.left || 50) / 100;
    collectResource({
      clientX: stage.getBoundingClientRect().left + stage.offsetWidth * left,
      clientY: stage.getBoundingClientRect().top + stage.offsetHeight * 0.72
    });
  }, 230);
}

function stopCollecting() {
  isCollecting = false;
  astronaut?.classList.remove("mining");
  clearInterval(collectTimer);
  collectTimer = null;
  saveState();
}

function claimCosmicBonus(event) {
  event.stopPropagation();
  if (!cosmicBonus) return;

  cosmicBonus.hidden = true;
  const burst = Math.max(25, Math.floor(getTotalRate() * 12 + getClickPower() * 18));
  const frenzy = Math.random() > 0.45;

  if (frenzy) {
    state.bonusMultiplier = 4;
    state.bonusUntil = Date.now() + 15000;
    addEvent("☄️ Cosmic frenzy active: production and harvests are x4 for 15 seconds.");
    showToast("☄️ Cosmic frenzy x4");
  } else {
    state.resources.oxygen += burst;
    state.resources.water += burst;
    state.resources.minerals += burst;
    state.score += burst * 12;
    addEvent(`☄️ Comet cache claimed: +${formatNumber(burst)} of every resource.`);
    showToast(`☄️ +${formatNumber(burst)} each`);
  }

  saveState();
  updateDisplay();
  scheduleCosmicBonus();
}

function scheduleCosmicBonus() {
  if (!cosmicBonus || !stage) return;
  const delay = 12000 + Math.random() * 22000;

  setTimeout(() => {
    if (!cosmicBonus || !stage) return;
    cosmicBonus.style.left = `${14 + Math.random() * 72}%`;
    cosmicBonus.style.top = `${18 + Math.random() * 48}%`;
    cosmicBonus.hidden = false;
    addEvent("☄️ A cosmic bonus appeared on the planet.");

    setTimeout(() => {
      if (!cosmicBonus.hidden) {
        cosmicBonus.hidden = true;
        scheduleCosmicBonus();
      }
    }, 8500);
  }, delay);
}

function buyUpgrade(type) {
  const config = upgradeConfig[type];
  const cost = getUpgradeCost(type);

  if (config.paysWith === "mixed") {
    const perResource = Math.floor(cost / 3);
    if (state.resources.oxygen < perResource || state.resources.water < perResource || state.resources.minerals < perResource) {
      addEvent(`⛔ Need ${formatNumber(perResource)} of each resource to upgrade ${config.label}.`);
      return;
    }
    state.resources.oxygen -= perResource;
    state.resources.water -= perResource;
    state.resources.minerals -= perResource;
  } else {
    if (state.resources[config.paysWith] < cost) {
      addEvent(`⛔ Need ${formatNumber(cost)} ${config.paysWith} for ${config.label}.`);
      return;
    }
    state.resources[config.paysWith] -= cost;
  }

  state.upgrades[type] += 1;
  state.score += cost * 3;
  addEvent(`${config.icon} ${config.label} upgraded to level ${state.upgrades[type]}.`);
  saveState();
  updateDisplay();

  if (backendEnabled) {
    apiRequest("/api/buy-upgrade", {
      method: "POST",
      body: JSON.stringify({ upgrade_type: type })
    })
      .then((payload) => {
        applyServerPayload(payload);
        updateDisplay();
      })
      .catch((error) => {
        addEvent(`⚠️ Upgrade sync failed: ${error.message}`);
        hydrateFromServer();
      });
  }
}

function addEvent(message) {
  if (!eventLog) return;
  const item = document.createElement("p");
  item.textContent = message;
  eventLog.prepend(item);

  while (eventLog.children.length > 5) {
    eventLog.lastElementChild.remove();
  }
}

function moveAstronautToNode(type) {
  const pos = nodePositions[type];
  astronaut.style.left = pos.left;
  astronaut.style.bottom = pos.bottom;
  astronaut.classList.add('mining');
  digEffect.textContent = `+${getResourceRate(type).toFixed(1)}`;
  digEffect.style.left = pos.left;
  digEffect.style.bottom = `${parseInt(pos.bottom) + 50}px`;
  digEffect.classList.add('show');
  digEffect.setAttribute('data-type', type);
  setTimeout(() => {
    astronaut.classList.remove('mining');
    digEffect.classList.remove('show');
    astronaut.style.left = '50%';
    astronaut.style.bottom = '145px';
  }, 1000);
}

function generatePassiveResources() {
  if (backendEnabled && pendingCollectRequests > 0) return;

  Object.keys(upgradeConfig).forEach((type) => {
    const rate = getResourceRate(type);
    if (rate > 0) {
      const amount = rate * getActiveMultiplier();
      state.resources[type] += amount;
      state.totalCollected += amount;
      state.score += amount * 4;
    }
  });

  // Move astronaut occasionally
  if (getTotalRate() > 0 && Date.now() - lastMove > 5000) {
    const types = Object.keys(nodePositions);
    const randomType = types[Math.floor(Math.random() * types.length)];
    moveAstronautToNode(randomType);
    lastMove = Date.now();
  }

  updateDisplay();
}

function rotateNews() {
  if (!newsTicker) return;
  const dynamicNews = [
    `Colony news: ${formatNumber(state.totalClicks)} harvests recorded.`,
    `Colony news: ${formatNumber(getTotalOwned())} machines are working.`,
    `Colony news: best combo is x${state.bestCombo}.`
  ];
  const messages = newsPool.concat(dynamicNews);
  newsTicker.textContent = messages[Math.floor(Math.random() * messages.length)];
}

function attachEvents() {
  if (stage) {
    stage.addEventListener("mousedown", (event) => {
      if (event.target.closest("button")) return;
      startCollecting(event);
    });
    stage.addEventListener("mousemove", (event) => {
      if (isCollecting) moveAstronaut(event);
    });
    window.addEventListener("mouseup", stopCollecting);

    stage.addEventListener("touchstart", (event) => {
      event.preventDefault();
      startCollecting(event.touches[0]);
    }, { passive: false });

    stage.addEventListener("touchmove", (event) => {
      event.preventDefault();
      if (isCollecting) moveAstronaut(event.touches[0]);
    }, { passive: false });

    window.addEventListener("touchend", stopCollecting);
  }

  document.querySelectorAll("[data-upgrade]").forEach((button) => {
    button.addEventListener("click", () => buyUpgrade(button.dataset.upgrade));
  });

  if (colonyCore) {
    colonyCore.addEventListener("mousedown", (event) => {
      event.stopPropagation();
      startCollecting(event);
    });
    colonyCore.addEventListener("touchstart", (event) => {
      event.preventDefault();
      event.stopPropagation();
      startCollecting(event.touches[0]);
    }, { passive: false });
  }

  if (cosmicBonus) {
    cosmicBonus.addEventListener("mousedown", claimCosmicBonus);
    cosmicBonus.addEventListener("touchstart", (event) => {
      event.preventDefault();
      claimCosmicBonus(event);
    }, { passive: false });
  }
}

attachEvents();
updateDisplay();
hydrateFromServer();
rotateNews();
scheduleCosmicBonus();
setInterval(generatePassiveResources, 1000);
setInterval(rotateNews, 6000);
autosaveTimer = setInterval(saveState, 5000);
window.addEventListener("beforeunload", () => {
  clearInterval(autosaveTimer);
  saveState();
});
