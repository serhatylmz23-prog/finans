export const SYK_FINANCE_BRANDS = Object.freeze({
  sykasif: "SyKâşif",
  syotagi: "SyOtağı",
  syfinansotagi: "SyFinansOtağı"
});

export class SYKFinansOtagiRuntime {
  constructor(options = {}) {
    this.root = options.root || document.documentElement;
    this.brand = options.brand || "syfinansotagi";
    this.brandVisible = options.brandVisible ?? true;
    this.brandAnimation = options.brandAnimation || "write";
    this.activeModule = options.activeModule || "bist";
    this.marketState = options.marketState || "closed";
    this.orderState = options.orderState || "idle";
    this.systemState = options.systemState || "active";
    this.riskLevel = options.riskLevel || "medium";
    this.progress = Number.isFinite(options.progress) ? options.progress : 0;
    this.confidence = Number.isFinite(options.confidence) ? options.confidence : 0;
    this.notificationCount = Number.isFinite(options.notificationCount)
      ? Math.max(0, Math.round(options.notificationCount))
      : 0;
    this.reducedMotion =
      window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches ?? false;
  }

  setBrand({ brand, visible, animation } = {}) {
    if (brand && Object.prototype.hasOwnProperty.call(SYK_FINANCE_BRANDS, brand)) {
      this.brand = brand;
    }
    if (typeof visible === "boolean") this.brandVisible = visible;
    if (animation) this.brandAnimation = animation;
    this.apply();
  }

  clearBrand(animation = "erase") {
    this.brandVisible = false;
    this.brandAnimation = animation;
    this.apply();
  }

  setActiveModule(moduleId) {
    this.activeModule = String(moduleId || "bist");
    this.apply();
  }

  setMarketState(state) {
    const allowed = ["preopen", "open", "auction", "closed", "holiday"];
    if (allowed.includes(state)) this.marketState = state;
    this.apply();
  }

  setOrderState(state) {
    const allowed = [
      "idle",
      "buy",
      "sell",
      "hold",
      "pending",
      "completed",
      "stopped"
    ];
    if (allowed.includes(state)) this.orderState = state;
    this.apply();
  }

  setSystemState(state) {
    const allowed = ["offline", "standby", "active", "warning", "critical"];
    if (allowed.includes(state)) this.systemState = state;
    this.apply();
  }

  setRiskLevel(level) {
    const allowed = ["low", "medium", "high", "critical"];
    if (allowed.includes(level)) this.riskLevel = level;
    this.apply();
  }

  setMetrics({ progress, confidence, notificationCount } = {}) {
    if (Number.isFinite(progress)) {
      this.progress = Math.max(0, Math.min(100, progress));
    }
    if (Number.isFinite(confidence)) {
      this.confidence = Math.max(0, Math.min(99.9, confidence));
    }
    if (Number.isFinite(notificationCount)) {
      this.notificationCount = Math.max(0, Math.round(notificationCount));
    }
    this.apply();
  }

  apply() {
    const r = this.root;

    r.dataset.sykFinanceBrand = this.brand;
    r.dataset.sykBrandVisible = this.brandVisible ? "true" : "false";
    r.dataset.sykBrandAnimation = this.brandAnimation;
    r.dataset.sykFinanceModule = this.activeModule;
    r.dataset.sykMarketState = this.marketState;
    r.dataset.sykOrderState = this.orderState;
    r.dataset.sykSystemState = this.systemState;
    r.dataset.sykRiskLevel = this.riskLevel;
    r.dataset.sykMotion = this.reducedMotion ? "reduced" : "full";

    r.style.setProperty("--syk-finance-progress", `${this.progress}%`);
    r.style.setProperty("--syk-finance-confidence", `${this.confidence}%`);
    r.style.setProperty("--syk-finance-notifications", `"${this.notificationCount}"`);

    window.dispatchEvent(new CustomEvent("syk:finance-state", {
      detail: this.getState()
    }));
  }

  getState() {
    return {
      brand: this.brand,
      brandText: SYK_FINANCE_BRANDS[this.brand],
      brandVisible: this.brandVisible,
      brandAnimation: this.brandAnimation,
      activeModule: this.activeModule,
      marketState: this.marketState,
      orderState: this.orderState,
      systemState: this.systemState,
      riskLevel: this.riskLevel,
      progress: this.progress,
      confidence: this.confidence,
      notificationCount: this.notificationCount,
      reducedMotion: this.reducedMotion
    };
  }
}

export function renderBrandTitle(element, runtime) {
  const sync = () => {
    const state = runtime.getState();
    element.textContent = state.brandVisible ? state.brandText : "";
    element.dataset.animation = state.brandAnimation;
    element.hidden = !state.brandVisible;
  };

  window.addEventListener("syk:finance-state", sync);
  sync();

  return () => window.removeEventListener("syk:finance-state", sync);
}
