const childProcess = require("child_process");

class ModuleWorker {
  constructor(isDev, modules, terminalWindow, log) {
    this._isDev = isDev;
    this._modules = modules;
    this._terminalWindow = terminalWindow;
    this._log = log;
  }

  run(file, cwd, args = []) {
    const subprocess = childProcess.spawn(file, args, {
      cwd: cwd,
      detached: true,
      windowsHide: true,
    });

    subprocess.stdout.on("data", (data) => {
      this._terminalWindow.ipcSend("asynchronous-reply", {
        id: file,
        data: data.toString("utf8"),
      });
    });

    subprocess.on("error", (err) => {
      this._log.error(`${file} error: `, err.message);
    });

    subprocess.on("close", (code, signal) => {
      this._log.error(`${file} closed: `, `Code: ${code}\nSignal: ${signal}`);
      setTimeout(() => {
        // this.run(file, cwd, args);
      }, 2000);
    });

    subprocess.unref();
  }

  isRunning(process, callback) {
    childProcess.exec("tasklist", (err, stdout) => {
      callback(stdout.toLowerCase().indexOf(process.toLowerCase()) > -1);
    });
  }

  setWatcher(procName, file, cwd) {
    const watcherId = setInterval(() => {
      this.isRunning(procName, (status) => {
        if (!status) {
          this.run(file, cwd);
          clearInterval(watcherId);
        }
      });
    }, 3000);
  }

  runAll() {
    if (this._isDev) return;

    console.log(`\nInitializing modules: ${this._modules}`);
    for (const module of this._modules) {
      const { procName, file, cwd } = module;
      console.log(`${procName}: `);

      this.isRunning(procName, (status) => {
        console.log(`${status ? "running\n" : "sleep\n"}`);
        if (!status) {
          this.run(file, cwd);
        } else {
          // this.setWatcher(procName, file, cwd);
        }
      });
    }
  }

  kill(name) {
    childProcess.exec(`TASKKILL /F /IM "${name}.exe" /T`, function (err, stdout, stderr) {
      if (err) this._log.error(`Subprocess(${name}) taskkill error!`, `stdout: ${stdout}\nstderr${stderr}`, true);
    });
  }

  killAll() {
    for (const module of this._modules) {
      this.kill(module.procName);
    }
  }
}

module.exports = ModuleWorker;
