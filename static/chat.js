(function () {
  "use strict";

  var SESSION_KEY = "vet-es-chat-session-id";

  function apiBase() {
    var raw = window.CHATBOT_API_BASE;
    if (raw === undefined || raw === null) {
      return "";
    }
    var s = String(raw).trim();
    while (s.endsWith("/")) {
      s = s.slice(0, -1);
    }
    return s;
  }

  function chatUrl() {
    var base = apiBase();
    return (base ? base : "") + "/chat";
  }

  function getOrCreateSessionId() {
    try {
      var existing = sessionStorage.getItem(SESSION_KEY);
      if (existing && existing.trim()) {
        return existing.trim();
      }
      var id =
        typeof crypto !== "undefined" && crypto.randomUUID
          ? crypto.randomUUID()
          : "s-" + String(Date.now()) + "-" + String(Math.random()).slice(2);
      sessionStorage.setItem(SESSION_KEY, id);
      return id;
    } catch (e) {
      return "fallback-session";
    }
  }

  function showError(el, text) {
    if (!text) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = text;
  }

  function appendMessage(logEl, role, text) {
    var row = document.createElement("div");
    row.className = "msg " + role;
    var label = document.createElement("div");
    label.className = "role";
    label.textContent = role === "user" ? "You" : "Assistant";
    var body = document.createElement("div");
    body.textContent = text;
    row.appendChild(label);
    row.appendChild(body);
    logEl.appendChild(row);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function formatFetchError(status, bodyText) {
    if (status === 422) {
      return "Request rejected (422). Check that the message is not empty.";
    }
    if (status >= 400) {
      return "Request failed (" + status + "). " + (bodyText || "").slice(0, 200);
    }
    return "Unexpected response (" + status + ").";
  }

  document.addEventListener("DOMContentLoaded", function () {
    var logEl = document.getElementById("chat-log");
    var form = document.getElementById("chat-form");
    var input = document.getElementById("msg-input");
    var errEl = document.getElementById("error-banner");
    var baseDisplay = document.getElementById("api-base-display");

    if (!logEl || !form || !input || !errEl) {
      return;
    }

    if (window.location.protocol === "file:") {
      showError(
        errEl,
        "This page was opened as a local file (file://). Open it from the API instead, " +
          "e.g. http://127.0.0.1:8000/ after running: python -m uvicorn main:app --reload"
      );
      if (baseDisplay) {
        baseDisplay.textContent = "(invalid — use http URL)";
      }
      return;
    }

    var base = apiBase();
    if (baseDisplay) {
      baseDisplay.textContent = base ? base : "(same origin)";
    }

    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      showError(errEl, "");

      var text = input.value.trim();
      if (!text) {
        showError(errEl, "Enter a non-empty message.");
        return;
      }

      appendMessage(logEl, "user", text);
      input.value = "";

      var sessionId = getOrCreateSessionId();
      var url = chatUrl();

      fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ msg: text, session_id: sessionId }),
      })
        .then(function (resp) {
          return resp.text().then(function (t) {
            return { resp: resp, text: t };
          });
        })
        .then(function (pair) {
          var resp = pair.resp;
          if (!resp.ok) {
            showError(errEl, formatFetchError(resp.status, pair.text));
            return;
          }
          var data;
          try {
            data = JSON.parse(pair.text);
          } catch (e) {
            showError(errEl, "Invalid JSON from server.");
            return;
          }
          var reply =
            data && typeof data.msg === "string" ? data.msg : String(pair.text);
          appendMessage(logEl, "assistant", reply);
        })
        .catch(function () {
          showError(
            errEl,
            "Network error — is the API running and CORS allowed for this origin?"
          );
        });
    });
  });
})();
