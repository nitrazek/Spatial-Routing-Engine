import tkinter as tk
from tkinter import messagebox
import tkintermapview

from src import enums


class RoutingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("System Nawigacji - Wyznaczanie Trasy")
        self.root.geometry("1000x700")

        # --- 1. Podział głównego okna na panele ---
        # Panel boczny (sterowanie) - po lewej stronie
        self.control_frame = tk.Frame(self.root, width=300, padx=20, pady=20)
        self.control_frame.pack(side="left", fill="y")

        # Panel mapy - po prawej stronie (zajmuje resztę miejsca)
        self.map_frame = tk.Frame(self.root)
        self.map_frame.pack(side="right", fill="both", expand=True)

        # --- 2. Inicjalizacja widgetu mapy ---
        self.map_widget = tkintermapview.TkinterMapView(self.map_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        # Ustawienie domyślnego widoku na Polskę
        self.map_widget.set_position(52.2297, 21.0122)
        self.map_widget.set_zoom(11)

        # --- 3. Budowa interfejsu w panelu bocznym ---
        self._build_controls()

        # Słownik do przypisania kolorów ścieżkom w zależności od trybu
        self.mode_colors = {
            enums.RouteMode.CAR: "#FF0000",
            enums.RouteMode.PUBLIC: "#0000FF",
            enums.RouteMode.PR: "#FF00FF"
        }

    def _build_controls(self):
        """Buduje formularz w lewym panelu."""
        tk.Label(self.control_frame, text="Współrzędne Startowe", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        tk.Label(self.control_frame, text="Szerokość (Lat):").pack(anchor="w")
        self.entry_source_lat = tk.Entry(self.control_frame)
        self.entry_source_lat.pack(fill="x", pady=(0, 5))
        self.entry_source_lat.insert(0, "52.1672") # Domyślna wartość dla testów

        tk.Label(self.control_frame, text="Długość (Lon):").pack(anchor="w")
        self.entry_source_lon = tk.Entry(self.control_frame)
        self.entry_source_lon.pack(fill="x", pady=(0, 15))
        self.entry_source_lon.insert(0, "20.9679") # Domyślna wartość dla testów

        tk.Label(self.control_frame, text="Współrzędne Celu", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        tk.Label(self.control_frame, text="Szerokość (Lat):").pack(anchor="w")
        self.entry_target_lat = tk.Entry(self.control_frame)
        self.entry_target_lat.pack(fill="x", pady=(0, 5))
        self.entry_target_lat.insert(0, "52.2478") # Domyślna wartość dla testów

        tk.Label(self.control_frame, text="Długość (Lon):").pack(anchor="w")
        self.entry_target_lon = tk.Entry(self.control_frame)
        self.entry_target_lon.pack(fill="x", pady=(0, 15))
        self.entry_target_lon.insert(0, "21.0144") # Domyślna wartość dla testów

        tk.Label(self.control_frame, text="Tryb transportu", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        # Zmienne przechowujące stan checkboxów (zaznaczony/odznaczony)
        self.mode_vars = {}
        for mode in enums.RouteMode:
            var = tk.BooleanVar(value=True if mode == enums.RouteMode.CAR else False)
            chk = tk.Checkbutton(self.control_frame, text=mode.value.upper(), variable=var)
            chk.pack(anchor="w")
            self.mode_vars[mode] = var

        # Przycisk uruchamiający algorytm
        btn_calc = tk.Button(self.control_frame, text="Wyznacz trasę", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), command=self.calculate_and_draw)
        btn_calc.pack(fill="x", pady=(30, 0))

    def calculate_and_draw(self):
        """Pobiera dane, wywołuje 'algorytm' i rysuje trasę na mapie."""
        # 1. Pobranie i walidacja współrzędnych
        try:
            source = (float(self.entry_source_lat.get()), float(self.entry_source_lon.get()))
            target = (float(self.entry_target_lat.get()), float(self.entry_target_lon.get()))
        except ValueError:
            messagebox.showerror("Błąd danych", "Współrzędne muszą być liczbami zmiennoprzecinkowymi!")
            return

        # 2. Pobranie zaznaczonych trybów
        selected_modes = [mode for mode, var in self.mode_vars.items() if var.get()]
        if not selected_modes:
            messagebox.showwarning("Brak trybu", "Wybierz przynajmniej jeden tryb transportu!")
            return

        # 3. Wyczyszczenie mapy przed nowym rysowaniem
        self.map_widget.delete_all_path()
        self.map_widget.delete_all_marker()

        # 4. Ustawienie markerów startu i końca
        self.map_widget.set_marker(source[0], source[1], text="START", marker_color_circle="green", marker_color_outside="darkgreen")
        self.map_widget.set_marker(target[0], target[1], text="CEL", marker_color_circle="red", marker_color_outside="darkred")

        # 5. Pętla po zaznaczonych trybach (analogicznie do CLI)
        for mode in selected_modes:
            # TODO: Tu podepnij swoje rzeczywiste wywołanie algorytmu:
            # nodes, cost = my_algorithm.run(source, target, mode)
            
            # --- MOCK DANYCH (Twój kod testowy) ---
            nodes = [
                source,  # Zastępujemy twardo zakodowany start podanym przez użytkownika
                target   # Zastępujemy twardo zakodowany cel podanym przez użytkownika
            ]

            # Jeśli wybraliśmy więcej niż jeden tryb naraz, w tym mocku narysują się jedne na drugich.
            # W prawdziwym systemie algorytm zwróci nieco inne punkty dla CAR, PUBLIC i PR.
            
            # Rysowanie ścieżki
            color = self.mode_colors.get(mode, "#000000")
            self.map_widget.set_path(
                position_list=nodes,
                color=color,
                width=4
            )

        # 6. Dostosowanie widoku mapy, aby objąć całą trasę
        # Obliczamy prosty środek między startem a celem
        min_lat = min(node[0] for node in nodes)
        max_lat = max(node[0] for node in nodes)
        min_lon = min(node[1] for node in nodes)
        max_lon = max(node[1] for node in nodes)
        self.map_widget.fit_bounding_box((max_lat, min_lon), (min_lat, max_lon))

if __name__ == "__main__":
    root = tk.Tk()
    app = RoutingApp(root)
    root.mainloop()