class AppState:
    """Grupează variabilele de stare ale aplicației pentru a reduce globalele."""

    def __init__(self) -> None:
        self.versiune_ollama_cache: str = "Se verifică versiunea..."
        self.model_activ_cache: str = "Se verifică..."
        self.resurse_cache: str = "—"
        self.service_details_cache: dict[str, str] = {
            "active_state": "checking",
            "sub_state": "pending",
            "active_timestamp": "",
        }
        self.selected_model_name: str | None = None
        self.comanda_in_curs: bool = False
        self.info_ollama_incarcare: bool = False
        self.model_incarcare_in_curs: bool = False
        self.service_info_incarcare: bool = False
        self.last_service_refresh_monotonic: float = 0.0
        self.last_version_refresh_monotonic: float = 0.0
        self.last_resource_refresh_monotonic: float = 0.0
