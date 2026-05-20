import tkinter as tk
from tkinter import messagebox
import tkintermapview

from src import enums


class RoutingApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("System Nawigacji - Wyznaczanie Trasy")
        self.root.geometry("1000x700")

        self.control_frame = tk.Frame(self.root, width=300, padx=20, pady=20)
        self.control_frame.pack(side="left", fill="y")

        self.map_frame = tk.Frame(self.root)
        self.map_frame.pack(side="right", fill="both", expand=True)

        self.map_widget = tkintermapview.TkinterMapView(self.map_frame, corner_radius=0)
        self.map_widget.pack(fill="both", expand=True)
        self.map_widget.set_position(52.2297, 21.0122)
        self.map_widget.set_zoom(11)

        self._build_controls()

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
        self.entry_source_lat.insert(0, "52.1672")

        tk.Label(self.control_frame, text="Długość (Lon):").pack(anchor="w")
        self.entry_source_lon = tk.Entry(self.control_frame)
        self.entry_source_lon.pack(fill="x", pady=(0, 15))
        self.entry_source_lon.insert(0, "20.9679")

        tk.Label(self.control_frame, text="Współrzędne Celu", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        tk.Label(self.control_frame, text="Szerokość (Lat):").pack(anchor="w")
        self.entry_target_lat = tk.Entry(self.control_frame)
        self.entry_target_lat.pack(fill="x", pady=(0, 5))
        self.entry_target_lat.insert(0, "52.2478")

        tk.Label(self.control_frame, text="Długość (Lon):").pack(anchor="w")
        self.entry_target_lon = tk.Entry(self.control_frame)
        self.entry_target_lon.pack(fill="x", pady=(0, 15))
        self.entry_target_lon.insert(0, "21.0144")

        tk.Label(self.control_frame, text="Tryb transportu", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.mode_vars = {}
        for mode in enums.RouteMode:
            var = tk.BooleanVar(value=True if mode == enums.RouteMode.CAR else False)
            chk = tk.Checkbutton(self.control_frame, text=mode.value.upper(), variable=var)
            chk.pack(anchor="w")
            self.mode_vars[mode] = var

        btn_calc = tk.Button(self.control_frame, text="Wyznacz trasę", bg="#4CAF50", fg="white", font=("Arial", 12, "bold"), command=self.calculate_and_draw)
        btn_calc.pack(fill="x", pady=(30, 0))

    def calculate_and_draw(self):
        """Pobiera dane, wywołuje 'algorytm' i rysuje trasę na mapie."""
        try:
            source = (float(self.entry_source_lat.get()), float(self.entry_source_lon.get()))
            target = (float(self.entry_target_lat.get()), float(self.entry_target_lon.get()))
        except ValueError:
            messagebox.showerror("Błąd danych", "Współrzędne muszą być liczbami zmiennoprzecinkowymi!")
            return

        selected_modes = [mode for mode, var in self.mode_vars.items() if var.get()]
        if not selected_modes:
            messagebox.showwarning("Brak trybu", "Wybierz przynajmniej jeden tryb transportu!")
            return

        self.map_widget.delete_all_path()
        self.map_widget.delete_all_marker()

        self.map_widget.set_marker(source[0], source[1], text="START", marker_color_circle="green", marker_color_outside="darkgreen")
        self.map_widget.set_marker(target[0], target[1], text="CEL", marker_color_circle="red", marker_color_outside="darkred")

        for mode in selected_modes:
            # --- MOCK DANYCH (Twój kod testowy) ---
            nodes = [
                source,
                target
            ]
            
            color = self.mode_colors.get(mode, "#000000")
            self.map_widget.set_path(
                position_list=nodes,
                color=color,
                width=4
            )

        min_lat = min(node[0] for node in nodes)
        max_lat = max(node[0] for node in nodes)
        min_lon = min(node[1] for node in nodes)
        max_lon = max(node[1] for node in nodes)
        self.map_widget.fit_bounding_box((max_lat, min_lon), (min_lat, max_lon))

if __name__ == "__main__":
    root = tk.Tk()
    app = RoutingApp(root)
    root.mainloop()
