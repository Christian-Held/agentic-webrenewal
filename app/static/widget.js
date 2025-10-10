/*! Bundled widget script generated from src/widget.ts. */
(function () {
  "use strict";

  function isLocalHost(url) {
    return ["localhost", "127.0.0.1", "0.0.0.0"].indexOf(url.hostname) !== -1;
  }

  function resolveScriptElement() {
    var current = document.currentScript;
    if (current && current.tagName) {
      return current;
    }
    return document.querySelector("script[data-embed-token]");
  }

  var ChatWidget = /** @class */ (function () {
    function ChatWidget(script) {
      var _this = this;
      this.listeners = {
        open: new Set(),
        close: new Set(),
      };
      this.opened = false;
      var embedToken = script.dataset ? script.dataset.embedToken : null;
      if (!embedToken) {
        throw new Error("Missing data-embed-token attribute on widget script tag");
      }
      if (!script.src) {
        throw new Error("Widget script tag must have a valid src attribute");
      }
      var scriptUrl = new URL(script.src, window.location.href);
      if (scriptUrl.protocol !== "https:" && !isLocalHost(scriptUrl)) {
        throw new Error("Widget script must be served over HTTPS or localhost for development");
      }
      this.script = script;
      this.token = embedToken;
      this.baseUrl = scriptUrl;
      this.elements = this.createElements();
      this.attach();
      this.api = {
        open: function () { return _this.open(); },
        close: function () { return _this.close(); },
        toggle: function () { return _this.toggle(); },
        isOpen: function () { return _this.opened; },
        on: function (event, listener) { return _this.addListener(event, listener); },
        off: function (event, listener) { return _this.removeListener(event, listener); },
      };
    }
    ChatWidget.prototype.createElements = function () {
      var container = document.createElement("div");
      container.setAttribute("data-widget", "feature-frontend");
      container.style.position = "fixed";
      container.style.inset = "0";
      container.style.display = "none";
      container.style.alignItems = "center";
      container.style.justifyContent = "flex-end";
      container.style.backgroundColor = "rgba(15, 23, 42, 0.35)";
      container.style.zIndex = "2147483000";
      container.style.padding = "0";
      var frameWrapper = document.createElement("div");
      frameWrapper.style.position = "relative";
      frameWrapper.style.width = "420px";
      frameWrapper.style.maxWidth = "90vw";
      frameWrapper.style.height = "620px";
      frameWrapper.style.maxHeight = "90vh";
      frameWrapper.style.margin = "0 24px 24px";
      frameWrapper.style.boxShadow = "0 24px 48px rgba(15, 23, 42, 0.25)";
      var iframe = document.createElement("iframe");
      iframe.title = "AI assistant";
      iframe.style.width = "100%";
      iframe.style.height = "100%";
      iframe.style.border = "0";
      iframe.style.borderRadius = "18px";
      iframe.style.backgroundColor = "#ffffff";
      iframe.setAttribute("sandbox", "allow-scripts allow-same-origin allow-forms");
      iframe.setAttribute("referrerpolicy", "strict-origin");
      iframe.setAttribute("loading", "lazy");
      var closeButton = document.createElement("button");
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
      var launchButton = document.createElement("button");
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
        container: container,
        frameWrapper: frameWrapper,
        iframe: iframe,
        launchButton: launchButton,
        closeButton: closeButton,
      };
    };
    ChatWidget.prototype.attach = function () {
      var _this = this;
      var container = this.elements.container, launchButton = this.elements.launchButton, closeButton = this.elements.closeButton;
      document.body.appendChild(container);
      document.body.appendChild(launchButton);
      container.addEventListener("click", function (event) {
        if (event.target === container) {
          _this.close();
        }
      });
      launchButton.addEventListener("click", function () { return _this.toggle(); });
      closeButton.addEventListener("click", function () { return _this.close(); });
    };
    ChatWidget.prototype.addListener = function (event, listener) {
      this.listeners[event].add(listener);
    };
    ChatWidget.prototype.removeListener = function (event, listener) {
      this.listeners[event].delete(listener);
    };
    ChatWidget.prototype.emit = function (event) {
      this.listeners[event].forEach(function (listener) {
        try {
          listener();
        } catch (error) {
          console.error("Widget listener execution failed", error);
        }
      });
    };
    ChatWidget.prototype.ensureIframeSource = function () {
      var iframe = this.elements.iframe;
      if (!iframe.src) {
        var embedUrl = new URL("/embed/chat", this.baseUrl.origin);
        embedUrl.searchParams.set("token", this.token);
        iframe.src = embedUrl.toString();
      }
    };
    ChatWidget.prototype.open = function () {
      if (this.opened) {
        return;
      }
      this.ensureIframeSource();
      this.elements.container.style.display = "flex";
      this.opened = true;
      this.emit("open");
    };
    ChatWidget.prototype.close = function () {
      if (!this.opened) {
        return;
      }
      this.elements.container.style.display = "none";
      this.opened = false;
      this.emit("close");
    };
    ChatWidget.prototype.toggle = function () {
      if (this.opened) {
        this.close();
      } else {
        this.open();
      }
    };
    return ChatWidget;
  })();

  function initializeWidget() {
    if (window.__featureFrontendWidgetInitialized__) {
      return;
    }
    var script = resolveScriptElement();
    if (!script) {
      console.error("feature-frontend: Unable to locate the widget <script> tag");
      return;
    }
    try {
      var widget = new ChatWidget(script);
      window.FeatureFrontendWidget = widget.api;
      window.__featureFrontendWidgetInitialized__ = true;
    } catch (error) {
      console.error("feature-frontend: Failed to bootstrap widget", error);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { return initializeWidget(); });
  } else {
    initializeWidget();
  }
})();
