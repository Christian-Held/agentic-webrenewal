/*
 * Lightweight embeddable chat widget for the feature frontend.
 * This file is authored in TypeScript and compiled to app/static/widget.js.
 */

type WidgetEvent = "open" | "close";
type WidgetListener = () => void;

interface WidgetAPI {
  open(): void;
  close(): void;
  toggle(): void;
  isOpen(): boolean;
  on(event: WidgetEvent, listener: WidgetListener): void;
  off(event: WidgetEvent, listener: WidgetListener): void;
}

declare global {
  interface Window {
    FeatureFrontendWidget?: WidgetAPI;
    __featureFrontendWidgetInitialized__?: boolean;
  }
}

interface WidgetElements {
  container: HTMLDivElement;
  frameWrapper: HTMLDivElement;
  iframe: HTMLIFrameElement;
  launchButton: HTMLButtonElement;
  closeButton: HTMLButtonElement;
}

function isLocalHost(url: URL): boolean {
  return ["localhost", "127.0.0.1", "0.0.0.0"].includes(url.hostname);
}

function resolveScriptElement(): HTMLScriptElement | null {
  const current = (document.currentScript as HTMLScriptElement | null);
  if (current) {
    return current;
  }

  return document.querySelector("script[data-embed-token]");
}

class ChatWidget {
  private readonly script: HTMLScriptElement;
  private readonly token: string;
  private readonly baseUrl: URL;
  private readonly elements: WidgetElements;
  private readonly listeners: Record<WidgetEvent, Set<WidgetListener>> = {
    open: new Set(),
    close: new Set(),
  };
  private opened = false;

  constructor(script: HTMLScriptElement) {
    const embedToken = script.dataset.embedToken;
    if (!embedToken) {
      throw new Error("Missing data-embed-token attribute on widget script tag");
    }

    if (!script.src) {
      throw new Error("Widget script tag must have a valid src attribute");
    }

    const scriptUrl = new URL(script.src, window.location.href);
    if (scriptUrl.protocol !== "https:" && !isLocalHost(scriptUrl)) {
      throw new Error("Widget script must be served over HTTPS or localhost for development");
    }

    this.script = script;
    this.token = embedToken;
    this.baseUrl = scriptUrl;
    this.elements = this.createElements();
    this.attach();
  }

  public get api(): WidgetAPI {
    return {
      open: () => this.open(),
      close: () => this.close(),
      toggle: () => this.toggle(),
      isOpen: () => this.opened,
      on: (event: WidgetEvent, listener: WidgetListener) => this.addListener(event, listener),
      off: (event: WidgetEvent, listener: WidgetListener) => this.removeListener(event, listener),
    };
  }

  private createElements(): WidgetElements {
    const container = document.createElement("div");
    container.setAttribute("data-widget", "feature-frontend");
    container.style.position = "fixed";
    container.style.inset = "0";
    container.style.display = "none";
    container.style.alignItems = "center";
    container.style.justifyContent = "flex-end";
    container.style.backgroundColor = "rgba(15, 23, 42, 0.35)";
    container.style.zIndex = "2147483000";
    container.style.padding = "0";

    const frameWrapper = document.createElement("div");
    frameWrapper.style.position = "relative";
    frameWrapper.style.width = "420px";
    frameWrapper.style.maxWidth = "90vw";
    frameWrapper.style.height = "620px";
    frameWrapper.style.maxHeight = "90vh";
    frameWrapper.style.margin = "0 24px 24px";
    frameWrapper.style.boxShadow = "0 24px 48px rgba(15, 23, 42, 0.25)";

    const iframe = document.createElement("iframe");
    iframe.title = "AI assistant";
    iframe.style.width = "100%";
    iframe.style.height = "100%";
    iframe.style.border = "0";
    iframe.style.borderRadius = "18px";
    iframe.style.backgroundColor = "#ffffff";
    iframe.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms");
    iframe.setAttribute("referrerpolicy", "strict-origin");
    iframe.setAttribute("loading", "lazy");

    const closeButton = document.createElement("button");
    closeButton.type = "button";
    closeButton.setAttribute("aria-label", "Close chat window");
    closeButton.innerHTML = "\u00d7";
    closeButton.style.position = "absolute";
    closeButton.style.top = "10px";
    closeButton.style.right = "10px";
    closeButton.style.width = "32px";
    closeButton.style.height = "32px";
    closeButton.style.borderRadius = "16px";
    closeButton.style.border = "none";
    closeButton.style.cursor = "pointer";
    closeButton.style.backgroundColor = "rgba(15, 23, 42, 0.8)";
    closeButton.style.color = "#ffffff";
    closeButton.style.display = "flex";
    closeButton.style.alignItems = "center";
    closeButton.style.justifyContent = "center";
    closeButton.style.fontSize = "20px";

    const launchButton = document.createElement("button");
    launchButton.type = "button";
    launchButton.setAttribute("aria-label", "Open AI assistant chat");
    launchButton.innerHTML = "\u2699";
    launchButton.style.position = "fixed";
    launchButton.style.bottom = "24px";
    launchButton.style.right = "24px";
    launchButton.style.width = "56px";
    launchButton.style.height = "56px";
    launchButton.style.borderRadius = "28px";
    launchButton.style.border = "none";
    launchButton.style.cursor = "pointer";
    launchButton.style.backgroundColor = "#2563eb";
    launchButton.style.color = "#ffffff";
    launchButton.style.boxShadow = "0 10px 30px rgba(37, 99, 235, 0.35)";
    launchButton.style.display = "flex";
    launchButton.style.alignItems = "center";
    launchButton.style.justifyContent = "center";
    launchButton.style.fontSize = "24px";
    launchButton.style.zIndex = "2147483001";

    frameWrapper.appendChild(iframe);
    frameWrapper.appendChild(closeButton);
    container.appendChild(frameWrapper);

    return {
      container,
      frameWrapper,
      iframe,
      launchButton,
      closeButton,
    };
  }

  private attach(): void {
    const { container, launchButton, closeButton } = this.elements;
    document.body.appendChild(container);
    document.body.appendChild(launchButton);

    container.addEventListener("click", (event) => {
      if (event.target === container) {
        this.close();
      }
    });

    launchButton.addEventListener("click", () => this.toggle());
    closeButton.addEventListener("click", () => this.close());
  }

  private addListener(event: WidgetEvent, listener: WidgetListener): void {
    this.listeners[event].add(listener);
  }

  private removeListener(event: WidgetEvent, listener: WidgetListener): void {
    this.listeners[event].delete(listener);
  }

  private emit(event: WidgetEvent): void {
    this.listeners[event].forEach((listener) => {
      try {
        listener();
      } catch (error) {
        console.error("Widget listener execution failed", error);
      }
    });
  }

  private ensureIframeSource(): void {
    const { iframe } = this.elements;
    if (!iframe.src) {
      const embedUrl = new URL("/embed/chat", this.baseUrl.origin);
      embedUrl.searchParams.set("token", this.token);
      iframe.src = embedUrl.toString();
    }
  }

  private open(): void {
    if (this.opened) {
      return;
    }

    this.ensureIframeSource();
    this.elements.container.style.display = "flex";
    this.opened = true;
    this.emit("open");
  }

  private close(): void {
    if (!this.opened) {
      return;
    }

    this.elements.container.style.display = "none";
    this.opened = false;
    this.emit("close");
  }

  private toggle(): void {
    if (this.opened) {
      this.close();
    } else {
      this.open();
    }
  }
}

function initializeWidget(): void {
  if (window.__featureFrontendWidgetInitialized__) {
    return;
  }

  const script = resolveScriptElement();
  if (!script) {
    console.error("feature-frontend: Unable to locate the widget <script> tag");
    return;
  }

  try {
    const widget = new ChatWidget(script);
    window.FeatureFrontendWidget = widget.api;
    window.__featureFrontendWidgetInitialized__ = true;
  } catch (error) {
    console.error("feature-frontend: Failed to bootstrap widget", error);
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => initializeWidget());
} else {
  initializeWidget();
}

export {};
