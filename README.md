# Ollama Control

Aplicatie desktop Python bazata pe CustomTkinter pentru controlul serviciului local Ollama si pentru gestionarea modelelor Ollama.

## Tehnologii

- Python 3.12 + CustomTkinter (interfata grafica)
- PyInstaller (ambalare in executabil si in pachete `.deb` / AppImage)

## Documentatie

- [Despre Ollama Control](Despre%20Ollama%20Control) - prezentare generala a aplicatiei si a capabilitatilor principale.


## Functionalitate

- pornire, oprire si restart pentru serviciul `ollama` prin `systemd` (cu `pkexec`);
- afisare stare serviciu, substate si uptime;
- afisare versiune client Ollama;
- detectare si monitorizare a modelului activ;
- monitorizare consum RAM si, daca exista GPU NVIDIA, VRAM;
- incarcare model Ollama cu confirmare reala din backend;
- buton de copiere pentru numele modelului activ;
- descarcarea modelelor direct din aplicatie, cu progres real in octeti;
- acces rapid la catalogul de modele de pe ollama.com;
- afisarea versiunii Ollama instalate si a celei mai recente, cu actualizare din aplicatie;
- bara de progres cu procent real la incarcarea modelului in memorie;
- eject model activ;
- afisarea caii de descarcare a modelelor, cu optiune de copiere si deschidere;
- creare modele derivate cu `PARAMETER num_ctx`;
- stergere modele Ollama;
- setari persistente pentru tema, auto-refresh, confirmare stop/restart si `keepalive`;
- jurnal local in `~/.ollama_control_ui/app.log`.

## Instalare din pachete prebuilt

Ambele variante folosesc acelasi executabil si includ toate dependintele Python.

### Pachet Debian / Ubuntu (.deb)

```bash
sudo apt install ./ollama-control_1.0.0_amd64.deb
```

Aplicatia se instaleaza in `/usr/lib/ollama-control/` si creeaza comanda `ollama-control`.

### AppImage

```bash
chmod +x ollama-control-x86_64.AppImage
./ollama-control-x86_64.AppImage
```

Nu necesita instalare. Daca FUSE nu este disponibil, se poate rula si dezarhivat:

```bash
./ollama-control-x86_64.AppImage --appimage-extract
./squashfs-root/AppRun
```

## Construire din sursa

### Executabil local

```bash
./venv/bin/pyinstaller ollama_control.spec --noconfirm
./dist/ollama_control/ollama_control
```

### Pachete de distributie

```bash
./packaging/build_all.sh
```

Scriptul construieste executabilul cu PyInstaller si produce atat pachetul `.deb`,
cat si AppImage, in directorul `release/`.

## Pornire locala

```bash
./start.sh
```

Scriptul activeaza mediul virtual din `venv/` si ruleaza `python ollama_control.py`.

## Setari

Setarile sunt pastrate in `~/.config/ollama-control/settings.json` (standard XDG),
pentru a functiona corect atunci cand aplicatia este instalata in `/usr/lib`
sau ruleaza dintr-un AppImage. La prima pornire, setarile din vechea locatie
(`settings.json` din directorul aplicatiei) sunt migrate automat.

## Teste

```bash
./venv/bin/python -m unittest discover -s tests -v
```

Suita include si o garda de regresie care verifica faptul ca proiectul
nu mai contine functionalitati sau mentiuni ale aplicatiei eliminate.
