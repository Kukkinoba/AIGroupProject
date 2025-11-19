import tkinter as tk
from tkinter import ttk, messagebox, filedialog

APP_TITLE = "Rural Pathfinder — GUI Shell"
APP_SIZE = "900x560"

CRITERIA_OPTIONS = [
    "shortest",
    "none",
    "avoid_unpaved",
    "avoid_cisterns",
    "avoid_potholes",
]

ROAD_TYPES = ["paved", "unpaved", "cistern", "potholes"]
ROAD_STATUS = ["open", "closed"]

# ---- fake in-memory dataset so the GUI feels alive (remove later)
FAKE_ROADS = [
    {"src": "a", "dst": "b", "dist": 5.0, "type": "paved", "status": "open"},
    {"src": "b", "dst": "c", "dist": 3.0, "type": "unpaved", "status": "open"},
    {"src": "c", "dst": "d", "dist": 7.0, "type": "paved", "status": "closed"},
    {"src": "a", "dst": "c", "dist": 10.0, "type": "paved", "status": "open"},
]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry(APP_SIZE)
        self.minsize(880, 520)

        self._build_style()
        self._build_menu()
        self._build_body()
        self._build_statusbar()

        # keyboard shortcuts
        self.bind_all("<Control-f>", lambda e: self._focus_route_finder())
        self.bind_all("<Control-n>", lambda e: self._focus_admin_add())
        self.bind_all("<F5>", lambda e: self._refresh_tables())

    # ---------- UI Shell ----------
    def _build_style(self):
        style = ttk.Style()
        # Use system default theme; if available, try "clam" for consistent look
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TButton", padding=(10, 6))
        style.configure("TLabel", padding=(2, 2))
        style.configure("Header.TLabel", font=("", 11, "bold"))

    def _build_menu(self):
        menubar = tk.Menu(self)
        # File
        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="Import roads…", command=self._on_import)
        file_menu.add_command(label="Export roads…", command=self._on_export)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.destroy, accelerator="Alt+F4")
        menubar.add_cascade(label="File", menu=file_menu)

        # View
        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_command(label="Refresh", command=self._refresh_tables, accelerator="F5")
        menubar.add_cascade(label="View", menu=view_menu)

        # Help
        help_menu = tk.Menu(menubar, tearoff=False)
        help_menu.add_command(label="About", command=self._about)
        menubar.add_cascade(label="Help", menu=help_menu)

        self.config(menu=menubar)

    def _build_body(self):
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(container)
        self.notebook.pack(fill="both", expand=True)

        self.route_tab = ttk.Frame(self.notebook)
        self.admin_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.route_tab, text="Route Finder")
        self.notebook.add(self.admin_tab, text="Admin")

        self._build_route_tab(self.route_tab)
        self._build_admin_tab(self.admin_tab)

    def _build_statusbar(self):
        bar = ttk.Frame(self, padding=(10, 4))
        bar.pack(fill="x", side="bottom")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(bar, textvariable=self.status_var).pack(side="left")
        ttk.Label(bar, text="Ctrl+F: Route Finder  •  Ctrl+N: Add Road  •  F5: Refresh")\
            .pack(side="right")

    # ---------- Route Finder Tab ----------
    def _build_route_tab(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        # Header
        ttk.Label(frm, text="Plan a Route", style="Header.TLabel").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 10))

        # Inputs
        ttk.Label(frm, text="Source").grid(row=1, column=0, sticky="w")
        self.src_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.src_var, width=22).grid(row=1, column=1, sticky="w", padx=(6, 16))

        ttk.Label(frm, text="Destination").grid(row=1, column=2, sticky="w")
        self.dst_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.dst_var, width=22).grid(row=1, column=3, sticky="w", padx=(6, 0))

        ttk.Label(frm, text="Criteria").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.criteria_var = tk.StringVar(value=CRITERIA_OPTIONS[0])
        ttk.Combobox(frm, textvariable=self.criteria_var, values=CRITERIA_OPTIONS, state="readonly", width=24)\
            .grid(row=2, column=1, sticky="w", padx=(6, 16), pady=(8, 0))

        self.find_btn = ttk.Button(frm, text="Find Route", command=self._on_find_route)
        self.find_btn.grid(row=2, column=2, columnspan=2, sticky="ew", pady=(8, 0))

        # Results table
        cols = ("#","Node")
        self.route_tree = ttk.Treeview(frm, columns=cols, show="headings", height=12)
        for c in cols:
            self.route_tree.heading(c, text=c)
            anchor = "e" if c == "#" else "w"
            width = 60 if c == "#" else 260
            self.route_tree.column(c, width=width, anchor=anchor)
        self.route_tree.grid(row=3, column=0, columnspan=4, sticky="nsew", pady=(12, 6))

        # Scrollbar
        yscroll = ttk.Scrollbar(frm, orient="vertical", command=self.route_tree.yview)
        self.route_tree.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=3, column=4, sticky="ns", padx=(6, 0))

        # Summary strip
        self.summary_var = tk.StringVar(value="Path: —   |   Distance: — km   |   Time: — min")
        ttk.Label(frm, textvariable=self.summary_var).grid(row=4, column=0, columnspan=4, sticky="w", pady=(6, 0))

        # Grid weights
        frm.columnconfigure(0, weight=0)
        frm.columnconfigure(1, weight=0)
        frm.columnconfigure(2, weight=1)
        frm.columnconfigure(3, weight=1)
        frm.rowconfigure(3, weight=1)

    # ---------- Admin Tab ----------
    def _build_admin_tab(self, parent):
        frm = ttk.Frame(parent, padding=10)
        frm.pack(fill="both", expand=True)

        ttk.Label(frm, text="Manage Roads", style="Header.TLabel").grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 10))

        ttk.Label(frm, text="Source").grid(row=1, column=0, sticky="w")
        self.a_src = tk.StringVar()
        ttk.Entry(frm, textvariable=self.a_src, width=16).grid(row=1, column=1, sticky="w", padx=(6, 16))

        ttk.Label(frm, text="Destination").grid(row=1, column=2, sticky="w")
        self.a_dst = tk.StringVar()
        ttk.Entry(frm, textvariable=self.a_dst, width=16).grid(row=1, column=3, sticky="w", padx=(6, 16))

        ttk.Label(frm, text="Distance (km)").grid(row=1, column=4, sticky="w")
        self.a_dist = tk.StringVar()
        ttk.Entry(frm, textvariable=self.a_dist, width=10).grid(row=1, column=5, sticky="w", padx=(6, 0))

        ttk.Label(frm, text="Type").grid(row=2, column=0, sticky="w", pady=(8, 0))
        self.a_type = tk.StringVar(value=ROAD_TYPES[0])
        ttk.Combobox(frm, textvariable=self.a_type, values=ROAD_TYPES, width=14, state="readonly")\
            .grid(row=2, column=1, sticky="w", padx=(6, 16), pady=(8, 0))

        ttk.Label(frm, text="Status").grid(row=2, column=2, sticky="w", pady=(8, 0))
        self.a_status = tk.StringVar(value=ROAD_STATUS[0])
        ttk.Combobox(frm, textvariable=self.a_status, values=ROAD_STATUS, width=14, state="readonly")\
            .grid(row=2, column=3, sticky="w", padx=(6, 16), pady=(8, 0))

        self.add_btn = ttk.Button(frm, text="Add", command=self._on_add_road)
        self.edit_btn = ttk.Button(frm, text="Edit Selected", command=self._on_edit_road)
        self.delete_btn = ttk.Button(frm, text="Delete Selected", command=self._on_delete_road)
        self.add_btn.grid(row=2, column=4, sticky="ew", padx=(0, 6), pady=(8, 0))
        self.edit_btn.grid(row=2, column=5, sticky="ew", padx=(0, 6), pady=(8, 0))
        self.delete_btn.grid(row=2, column=6, sticky="ew", pady=(8, 0))

        # Roads table
        cols = ("Source","Destination","Distance (km)","Type","Status")
        self.roads_tree = ttk.Treeview(frm, columns=cols, show="headings", height=12, selectmode="browse")
        for c in cols:
            self.roads_tree.heading(c, text=c)
            width = {"Source":110,"Destination":120,"Distance (km)":110,"Type":110,"Status":90}[c]
            anchor = "center" if c in ("Distance (km)","Status") else "w"
            self.roads_tree.column(c, width=width, anchor=anchor)
        self.roads_tree.grid(row=3, column=0, columnspan=7, sticky="nsew", pady=(12, 6))

        yscroll = ttk.Scrollbar(frm, orient="vertical", command=self.roads_tree.yview)
        self.roads_tree.configure(yscrollcommand=yscroll.set)
        yscroll.grid(row=3, column=7, sticky="ns", padx=(6, 0))

        frm.rowconfigure(3, weight=1)
        for i in range(7):
            frm.columnconfigure(i, weight=1)

        # preload fake data
        self._load_fake_roads()

    # ---------- Menu actions (stubs) ----------
    def _on_import(self):
        file = filedialog.askopenfilename(title="Import roads", filetypes=[("Prolog/CSV","*.pl *.csv"),("All files","*.*")])
        if not file:
            return
        # TODO: replace with real import later
        self.status_var.set(f"Imported: {file}")
        messagebox.showinfo("Import", "Import success (stub).")
        self._refresh_tables()

    def _on_export(self):
        file = filedialog.asksaveasfilename(title="Export roads", defaultextension=".pl",
                                            filetypes=[("Prolog","*.pl"),("CSV","*.csv"),("All files","*.*")])
        if not file:
            return
        # TODO: replace with real export later
        self.status_var.set(f"Exported to: {file}")
        messagebox.showinfo("Export", "Export success (stub).")

    def _about(self):
        messagebox.showinfo("About", "Rural Pathfinder GUI\nTkinter/ttk shell.\nLogic will be added later.")

    # ---------- Route Finder actions (stubs) ----------
    def _on_find_route(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        crit = self.criteria_var.get()

        # basic UI validation only
        if not src or not dst:
            messagebox.showwarning("Missing input", "Please enter both Source and Destination.")
            return
        if src == dst:
            messagebox.showwarning("Same nodes", "Source and Destination must be different.")
            return

        # clear table + fill with a fake path for now
        for i in self.route_tree.get_children():
            self.route_tree.delete(i)
        fake_path = [src, "…", dst]
        for idx, node in enumerate(fake_path, start=1):
            self.route_tree.insert("", "end", values=(idx, node))

        # fake summary
        self.summary_var.set(f"Path: {fake_path}   |   Distance: — km   |   Time: — min")
        self.status_var.set(f"Planned route ({crit}) [stub].")

    # ---------- Admin actions (stubs) ----------
    def _load_fake_roads(self):
        for i in self.roads_tree.get_children():
            self.roads_tree.delete(i)
        for r in FAKE_ROADS:
            self.roads_tree.insert("", "end", values=(r["src"], r["dst"], r["dist"], r["type"], r["status"]))

    def _on_add_road(self):
        s = self.a_src.get().strip()
        d = self.a_dst.get().strip()
        dist = self.a_dist.get().strip()
        t = self.a_type.get()
        st = self.a_status.get()

        # UI validation only
        if not s or not d or not dist:
            messagebox.showwarning("Missing fields", "Source, Destination and Distance are required.")
            return
        try:
            float(dist)
        except ValueError:
            messagebox.showwarning("Invalid distance", "Distance must be a number.")
            return
        if s == d:
            messagebox.showwarning("Same nodes", "Source and Destination must be different.")
            return

        # pretend to add to dataset
        self.roads_tree.insert("", "end", values=(s, d, float(dist), t, st))
        self.status_var.set("Road added (stub).")
        self.a_src.set(""); self.a_dst.set(""); self.a_dist.set("")

    def _on_edit_road(self):
        item = self.roads_tree.selection()
        if not item:
            messagebox.showinfo("Edit", "Select one road to edit.")
            return
        # For now, just a stub dialog
        messagebox.showinfo("Edit", "Open edit dialog (stub).")

    def _on_delete_road(self):
        item = self.roads_tree.selection()
        if not item:
            messagebox.showinfo("Delete", "Select one road to delete.")
            return
        self.roads_tree.delete(item)
        self.status_var.set("Road deleted (stub).")

    # ---------- Utility ----------
    def _refresh_tables(self):
        self._load_fake_roads()
        self.status_var.set("Tables refreshed.")

    def _focus_route_finder(self):
        self.notebook.select(self.route_tab)
        self.src_var.set("")
        self.dst_var.set("")
        self.status_var.set("Focused: Route Finder.")

    def _focus_admin_add(self):
        self.notebook.select(self.admin_tab)
        # focus first input
        for child in self.admin_tab.winfo_children():
            for sub in child.winfo_children():
                if isinstance(sub, ttk.Entry):
                    sub.focus_set()
                    self.status_var.set("Focused: Admin (Add).")
                    return

if __name__ == "__main__":
    App().mainloop()
