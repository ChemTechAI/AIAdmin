function addClickHandler(el) {
  el.addEventListener("click", function () {
    this.classList.toggle("active");
    const terminal = this.nextElementSibling;
    console.log(terminal.style.maxHeight);
    console.log(terminal.style.height);
    if (terminal.style.maxHeight) {
      terminal.style.maxHeight = null;
      terminal.style.height = null;
    } else {
      terminal.style.maxHeight = "500px";
      terminal.style.height = "500px";
    }
  });
}

function update(id, data) {
  const term = document.getElementById(id);

  const isScrolledToBottom = term.scrollHeight - term.clientHeight <= term.scrollTop + 1;

  term.innerHTML += `<br>${data}`;

  if(isScrolledToBottom) term.scrollTop = term.scrollHeight - term.clientHeight;
}

function createNewTerminal(id) {
  const root = document.getElementById("root");
  const termRoot = document.createElement("div");
  const acc = document.createElement("button");
  const term = document.createElement("p");

  acc.textContent = id;
  acc.setAttribute("class", "accordion");
  term.setAttribute("id", id);
  term.setAttribute("class", "terminal");

  termRoot.appendChild(acc);
  termRoot.appendChild(term);

  root.appendChild(termRoot);

  addClickHandler(acc);
}

function checkTerminal(id) {
  const el = document.getElementById(id);
  if (el == null) createNewTerminal(id);
}

function writeNewLog(id, data) {
  const termId = id + "-term";
  checkTerminal(termId);
  update(termId, data);
}
