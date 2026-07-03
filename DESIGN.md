<!DOCTYPE html>

<html lang="tr"><head>
<meta charset="utf-8"/>
<meta content="width=device-width, initial-scale=1.0" name="viewport"/>
<title>PortföyAI - Dashboard</title>
<script src="https://cdn.tailwindcss.com?plugins=forms,container-queries"></script>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com" rel="preconnect"/>
<link crossorigin="" href="https://fonts.gstatic.com" rel="preconnect"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&amp;family=Plus+Jakarta+Sans:wght@400;500;600;700;800&amp;display=swap" rel="stylesheet"/>
<link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&amp;display=swap" rel="stylesheet"/>
<script id="tailwind-config">
        tailwind.config = {
            darkMode: "class",
            theme: {
                extend: {
                    colors: {
                        "on-secondary": "#ffffff",
                        "surface-container-low": "#f3f4f5",
                        "primary-fixed-dim": "#bec6e0",
                        "on-error-container": "#93000a",
                        "error": "#ba1a1a",
                        "surface-glass": "rgba(255, 255, 255, 0.7)",
                        "mint-accent": "#E0F2F1",
                        "on-surface-variant": "#45464d",
                        "surface-bright": "#f8f9fa",
                        "inverse-surface": "#2e3132",
                        "on-background": "#191c1d",
                        "secondary-fixed": "#9feffe",
                        "on-secondary-fixed": "#001f24",
                        "on-tertiary-fixed": "#221b02",
                        "error-container": "#ffdad6",
                        "gold-leaf": "#D4AF37",
                        "surface-container-highest": "#e1e3e4",
                        "on-secondary-fixed-variant": "#004f59",
                        "primary": "#000000",
                        "surface-dim": "#d9dadb",
                        "surface-container-high": "#e7e8e9",
                        "on-primary-fixed": "#131b2e",
                        "tertiary": "#695e3d",
                        "background": "#f8f9fa",
                        "tertiary-fixed-dim": "#d5c69d",
                        "on-tertiary-fixed-variant": "#504627",
                        "on-tertiary-container": "#483f20",
                        "on-primary-container": "#7c839b",
                        "surface-container-lowest": "#ffffff",
                        "inverse-primary": "#bec6e0",
                        "outline": "#76777d",
                        "tertiary-container": "#b8aa83",
                        "surface-variant": "#e1e3e4",
                        "text-muted": "#64748B",
                        "surface-container": "#edeeef",
                        "on-primary": "#ffffff",
                        "on-tertiary": "#ffffff",
                        "surface-tint": "#565e74",
                        "on-surface": "#191c1d",
                        "on-secondary-container": "#016d7a",
                        "on-error": "#ffffff",
                        "primary-container": "#131b2e",
                        "surface": "#f8f9fa",
                        "primary-fixed": "#dae2fd",
                        "outline-variant": "#c6c6cd",
                        "tertiary-fixed": "#f1e1b8",
                        "secondary-container": "#9cecfb",
                        "inverse-on-surface": "#f0f1f2",
                        "secondary-fixed-dim": "#83d3e1",
                        "on-primary-fixed-variant": "#3f465c",
                        "secondary": "#006875"
                    },
                    borderRadius: {
                        "DEFAULT": "1rem",
                        "lg": "2rem",
                        "xl": "3rem",
                        "full": "9999px"
                    },
                    spacing: {
                        "gutter": "24px",
                        "section-margin": "48px",
                        "container-padding": "32px",
                        "card-gap": "20px",
                        "unit": "8px"
                    },
                    fontFamily: {
                        "title-md": ["Plus Jakarta Sans"],
                        "label-caps": ["Inter"],
                        "headline-lg": ["Plus Jakarta Sans"],
                        "body-sm": ["Plus Jakarta Sans"],
                        "headline-lg-mobile": ["Plus Jakarta Sans"],
                        "display-lg": ["Plus Jakarta Sans"],
                        "body-lg": ["Plus Jakarta Sans"]
                    },
                    fontSize: {
                        "title-md": ["20px", { "lineHeight": "28px", "fontWeight": "600" }],
                        "label-caps": ["12px", { "lineHeight": "16px", "letterSpacing": "0.05em", "fontWeight": "600" }],
                        "headline-lg": ["32px", { "lineHeight": "40px", "fontWeight": "600" }],
                        "body-sm": ["14px", { "lineHeight": "20px", "fontWeight": "400" }],
                        "headline-lg-mobile": ["24px", { "lineHeight": "32px", "fontWeight": "600" }],
                        "display-lg": ["48px", { "lineHeight": "56px", "letterSpacing": "-0.02em", "fontWeight": "700" }],
                        "body-lg": ["16px", { "lineHeight": "24px", "fontWeight": "400" }]
                    }
                }
            }
        }
    </script>
<style>
        .material-symbols-outlined {
            font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        .icon-fill {
            font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        }
        .glass-panel {
            background: rgba(255, 255, 255, 0.7);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.5);
        }
    </style>
</head>
<body class="bg-background text-on-surface font-body-sm antialiased flex h-screen overflow-hidden">
<!-- SideNavBar (Shared Component) -->
<nav class="hidden md:flex fixed left-0 top-0 h-full w-72 flex-col p-6 z-40 bg-surface-container-lowest dark:bg-surface-container-low shadow-[0px_10px_30px_rgba(0,0,0,0.04)]">
<div class="mb-12">
<h1 class="font-headline-lg text-headline-lg font-black text-primary tracking-tight">PortföyAI</h1>
<p class="text-on-surface-variant font-body-sm mt-1">Closing Assistant</p>
</div>
<ul class="flex flex-col gap-2 flex-1">
<li>
<a class="flex items-center gap-4 bg-mint-accent text-primary rounded-xl px-4 py-3 font-bold scale-98 transition-transform hover:bg-mint-accent/50 transition-all duration-200" href="#">
<span class="material-symbols-outlined icon-fill">dashboard</span>
<span class="font-title-md text-[16px]">Dashboard</span>
</a>
</li>
<li>
<a class="flex items-center gap-4 text-on-surface-variant px-4 py-3 hover:bg-surface-container-low rounded-xl hover:bg-mint-accent/50 transition-all duration-200 font-medium" href="#">
<span class="material-symbols-outlined">home_work</span>
<span class="font-title-md text-[16px] text-muted">İlanlar</span>
</a>
</li>
<li>
<a class="flex items-center gap-4 text-on-surface-variant px-4 py-3 hover:bg-surface-container-low rounded-xl hover:bg-mint-accent/50 transition-all duration-200 font-medium" href="#">
<span class="material-symbols-outlined">group</span>
<span class="font-title-md text-[16px] text-muted">Adaylar</span>
</a>
</li>
<li>
<a class="flex items-center gap-4 text-on-surface-variant px-4 py-3 hover:bg-surface-container-low rounded-xl hover:bg-mint-accent/50 transition-all duration-200 font-medium" href="#">
<span class="material-symbols-outlined">psychology</span>
<span class="font-title-md text-[16px] text-muted">YZ Asistanı</span>
</a>
</li>
<li>
<a class="flex items-center gap-4 text-on-surface-variant px-4 py-3 hover:bg-surface-container-low rounded-xl hover:bg-mint-accent/50 transition-all duration-200 font-medium" href="#">
<span class="material-symbols-outlined">assessment</span>
<span class="font-title-md text-[16px] text-muted">Reports</span>
</a>
</li>
</ul>
<div class="mt-auto pt-6 border-t border-surface-variant">
<button class="w-full bg-primary text-on-primary rounded-full py-4 px-6 flex items-center justify-center gap-2 shadow-md hover:shadow-lg transition-all mb-6">
<span class="material-symbols-outlined">mic</span>
<span class="font-label-caps text-[14px]">Voice-to-Listing</span>
</button>
<ul class="flex flex-col gap-2">
<li>
<a class="flex items-center gap-4 text-on-surface-variant px-4 py-2 hover:bg-surface-container-low rounded-xl transition-colors" href="#">
<span class="material-symbols-outlined">help</span>
<span class="font-body-sm text-muted">Support</span>
</a>
</li>
<li>
<a class="flex items-center gap-4 text-on-surface-variant px-4 py-2 hover:bg-surface-container-low rounded-xl transition-colors" href="#">
<span class="material-symbols-outlined">person</span>
<span class="font-body-sm text-muted">Account</span>
</a>
</li>
</ul>
</div>
</nav>
<!-- Main Content Area -->
<main class="flex-1 md:ml-72 h-full overflow-y-auto bg-background p-4 md:p-8">
<!-- Header (Contextual) -->
<header class="flex justify-between items-center mb-8">
<div>
<h2 class="font-headline-lg text-headline-lg text-primary">Genel Bakış</h2>
<p class="text-text-muted font-body-sm mt-1">Toplam: <span class="font-bold text-primary">1,293</span> ilan aktif.</p>
</div>
<div class="flex items-center gap-4">
<div class="glass-panel rounded-full px-4 py-2 flex items-center gap-2 text-text-muted shadow-sm hidden md:flex">
<span class="material-symbols-outlined">search</span>
<input class="bg-transparent border-none focus:ring-0 text-sm outline-none w-48" placeholder="İlan veya müşteri ara..." type="text"/>
</div>
<button class="w-10 h-10 rounded-full bg-surface-container-lowest shadow-sm flex items-center justify-center text-text-muted hover:text-primary transition-colors">
<span class="material-symbols-outlined">notifications</span>
</button>
<img class="w-10 h-10 rounded-full object-cover shadow-sm border-2 border-white" data-alt="A professional headshot of a real estate agent, smiling warmly, bright lighting, clean background, modern corporate style." src="https://lh3.googleusercontent.com/aida-public/AB6AXuCZAlPkDk1kMMPEdwa5qPedVCveIis-OqZwm6qogB-FHaFWgy3Akk6BVI57yxDsJ4pedpyPnZUgQLjZyyqnlZut56Gik75-Af7KL-k3K6tcgy2QwT0YHfbjkSmwJjQKuqgH04ecjIXxBLrmdj-yhTVWYbbFQKJUwrZenmu64ByTtgaU6nZkMtMYpmEPFk5czDQC-fs1AKnzVdS0MCrxzq4XXxXK6hUvoDXhk3ZpdYoKum607eB44bMk"/>
</div>
</header>
<!-- Bento Grid Layout -->
<div class="grid grid-cols-1 xl:grid-cols-12 gap-gutter max-w-[1440px] mx-auto">
<!-- Left Area: Property Cards (8 columns) -->
<div class="xl:col-span-8 flex flex-col gap-6">
<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
<!-- Property Card 1 -->
<div class="bg-surface-container-lowest rounded-lg p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] hover:shadow-[0px_15px_40px_rgba(0,0,0,0.08)] transition-shadow duration-300 flex flex-col">
<div class="flex justify-between items-start mb-4 px-2">
<div class="flex items-center gap-3">
<div class="w-10 h-10 rounded-full bg-mint-accent flex items-center justify-center text-secondary">
<span class="material-symbols-outlined">apartment</span>
</div>
<div>
<h3 class="font-title-md text-title-md text-primary leading-tight">Casa Solara</h3>
<p class="text-text-muted font-body-sm text-[12px]">128 Güneş Sokak</p>
</div>
</div>
<button class="text-outline hover:text-error transition-colors">
<span class="material-symbols-outlined">favorite</span>
</button>
</div>
<div class="flex gap-2 mb-4 px-2 flex-wrap">
<span class="bg-surface-container text-on-surface font-label-caps text-[10px] px-2 py-1 rounded-DEFAULT">120 m²</span>
<span class="bg-surface-container text-on-surface font-label-caps text-[10px] px-2 py-1 rounded-DEFAULT">3 Oda</span>
<span class="bg-surface-container text-on-surface font-label-caps text-[10px] px-2 py-1 rounded-DEFAULT">2 Banyo</span>
</div>
<div class="relative w-full h-48 rounded-DEFAULT overflow-hidden mt-auto">
<img class="w-full h-full object-cover" data-alt="A modern, high-end residential apartment building exterior with large windows and a clean, minimalist facade in bright daylight." src="https://lh3.googleusercontent.com/aida-public/AB6AXuCgo5PmGCauUR1cTOxWgkjT1ie6o5cICmRUHfA8zwLZOzNdu05z_bY8_cUtbwnnk0LAoWHN2lZwTaiDykT5tTM_uyLFnwgF2d1WCQ9BUSuk5r1UPAhKGPDfnRrDvyc1VX_EOtlFtDZ6vNjijgauUM7MUoAATl7PLwuy5BGI8s6Hv7xLJLY-L8ae2-8fXhZwIDCS5CSltq7rRHlwAo_cwSb0odADQNnZ-1M4r2x19lTonc-nOyvjimO1"/>
<button class="absolute bottom-3 right-3 bg-primary text-on-primary px-4 py-2 rounded-full font-label-caps text-[12px] shadow-lg hover:scale-105 transition-transform">
                                İncele
                            </button>
</div>
</div>
<!-- Property Card 2 -->
<div class="bg-surface-container-lowest rounded-lg p-4 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] hover:shadow-[0px_15px_40px_rgba(0,0,0,0.08)] transition-shadow duration-300 flex flex-col">
<div class="flex justify-between items-start mb-4 px-2">
<div class="flex items-center gap-3">
<div class="w-10 h-10 rounded-full bg-mint-accent flex items-center justify-center text-secondary">
<span class="material-symbols-outlined">house</span>
</div>
<div>
<h3 class="font-title-md text-title-md text-primary leading-tight">Villa Esperanza</h3>
<p class="text-text-muted font-body-sm text-[12px]">237 Umut Bulvarı</p>
</div>
</div>
<button class="text-outline hover:text-error transition-colors">
<span class="material-symbols-outlined">favorite</span>
</button>
</div>
<div class="flex gap-2 mb-4 px-2 flex-wrap">
<span class="bg-surface-container text-on-surface font-label-caps text-[10px] px-2 py-1 rounded-DEFAULT">240 m²</span>
<span class="bg-surface-container text-on-surface font-label-caps text-[10px] px-2 py-1 rounded-DEFAULT">5 Oda</span>
<span class="bg-surface-container text-on-surface font-label-caps text-[10px] px-2 py-1 rounded-DEFAULT">3 Banyo</span>
</div>
<div class="relative w-full h-48 rounded-DEFAULT overflow-hidden mt-auto">
<img class="w-full h-full object-cover" data-alt="A stunning contemporary luxury villa exterior with brick accents, wide terraces, and lush green surroundings in soft morning light." src="https://lh3.googleusercontent.com/aida-public/AB6AXuAM1z3dqEUSR2IQSle3OzaRPUVnEQlOrrsi1aN5oVJzLh4NWP_ak0fjayBSxwdYxWhyq6xfJRUELvUR3SsVnxUyC1biYOon4iG_rO2JCx6zAnb5GuiaEHaHn_B4akOnwi2sNbNnuob9-dribrMH9S9-5BxBgzfYFg-YLP_64UjwD9uf0y6B_PDJezrHs0UBARWVutFTKyZ7dQWMnjr_oWNwY0E97E65kphj6tfako9V6JfDl9od7zws"/>
<button class="absolute bottom-3 right-3 bg-primary text-on-primary px-4 py-2 rounded-full font-label-caps text-[12px] shadow-lg hover:scale-105 transition-transform">
                                İncele
                            </button>
</div>
</div>
</div>
</div>
<!-- Right Area: Middle & Side Panels (4 columns) -->
<div class="xl:col-span-4 flex flex-col gap-6">
<!-- Add Property Card -->
<div class="bg-surface-container-lowest rounded-lg p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] h-64 border-2 border-dashed border-outline-variant flex flex-col items-center justify-center cursor-pointer hover:bg-surface-bright transition-colors relative overflow-hidden group">
<div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNDAiIGhlaWdodD0iNDAiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+PGRlZnM+PHBhdHRlcm4gaWQ9InBhdHRlcm4iIHdpZHRoPSI0MCIgaGVpZ2h0PSI0MCIgcGF0dGVyblVuaXRzPSJ1c2VyU3BhY2VPblVzZSI+PHBhdGggZD0iTTAgNDBMMDAgMEw0MCA0MFoiIGZpbGw9Im5vbmUiIHN0cm9rZT0iI2UxZTNlNCIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI3BhdHRlcm4pIi8+PC9zdmc+')] opacity-50"></div>
<div class="w-12 h-12 rounded-full bg-white shadow-md flex items-center justify-center text-primary group-hover:scale-110 transition-transform z-10 mb-4">
<span class="material-symbols-outlined">add</span>
</div>
<p class="font-title-md text-[16px] text-primary z-10 font-medium">Yeni İlan Ekle</p>
</div>
<!-- Recent Messages & Leads -->
<div class="bg-surface-container-lowest rounded-lg p-6 shadow-[0px_10px_30px_rgba(0,0,0,0.04)] flex-1 flex flex-col">
<div class="flex justify-between items-center mb-6">
<h3 class="font-title-md text-[18px] text-primary">Aday Mesajları</h3>
<span class="bg-mint-accent text-secondary font-label-caps px-2 py-1 rounded-DEFAULT text-[10px]">YZ Destekli</span>
</div>
<div class="flex flex-col gap-4 overflow-y-auto max-h-[400px] pr-2">
<!-- Message Item 1 -->
<div class="flex gap-4 p-3 rounded-DEFAULT hover:bg-surface-bright transition-colors cursor-pointer border border-transparent hover:border-surface-variant">
<img class="w-12 h-12 rounded-full object-cover shrink-0" data-alt="A casual portrait of a young female client, smiling, bright and approachable, outdoor lighting." src="https://lh3.googleusercontent.com/aida-public/AB6AXuDnYGMa4Or-eW3p9bg5ALyIc8X4qN4gtMTEh6b_B1ctxMtEsbL6L6hoJytTVQhlcwtLkS1CgAxfk-BA857g0zl6W1wNCnf6xmIZdkNujfJfxpHQPgro59Q7BRjkyh38Bg7nCvLg0SdJfJklALmnMwfMvFOSw5qss6pydayNgt2kVltkmBZJiwcLqtM5ndhz1zRtk7kFUHB2SQgBXKl1gU2ZmxlV-pEhCWmcPDN6efH7UEvhVnQrjU7o"/>
<div class="flex-1">
<div class="flex justify-between items-start">
<h4 class="font-body-sm font-semibold text-primary">Ayşe Yılmaz</h4>
<span class="text-[10px] text-text-muted">Bugün</span>
</div>
<p class="text-[12px] text-text-muted mt-1 line-clamp-2">Merhaba, modern ve merkeze yakın bir daire arıyorum. Bütçem esnek, elinizdeki...</p>
<div class="mt-2 flex items-center gap-2">
<span class="bg-green-100 text-green-800 font-label-caps text-[9px] px-2 py-0.5 rounded-full">%95 Eşleşme</span>
</div>
</div>
<div class="flex items-center text-outline">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</div>
<!-- Message Item 2 -->
<div class="flex gap-4 p-3 rounded-DEFAULT hover:bg-surface-bright transition-colors cursor-pointer border border-transparent hover:border-surface-variant">
<img class="w-12 h-12 rounded-full object-cover shrink-0" data-alt="A professional headshot of a male client in his 30s, neutral expression, clean corporate background." src="https://lh3.googleusercontent.com/aida-public/AB6AXuBALN6Vbi5hsUizifDopdUYzcO7WyeiHA3IQMrOqLYR-ur05gjzUgmjV8SZ_Cwo4oKkI1prX6KXbVh9cvTG7WGlPQf-iQTshJ7LpmTlNcYsIu8Qy7gptByTr558bED0Y_hW_Lv2K1tKwnYlJ79Jl4FIU3BuD4c8cUpqCyDYMC5raOO6zgiZ5gnOROFwOEU7VYBhSZHHCuNRKBqJ40P1H7HmNGlxmc_nbUeM_benmBo-nJ0YHT-cdOEl"/>
<div class="flex-1">
<div class="flex justify-between items-start">
<h4 class="font-body-sm font-semibold text-primary">Caner Öztürk</h4>
<span class="text-[10px] text-text-muted">Dün</span>
</div>
<p class="text-[12px] text-text-muted mt-1 line-clamp-2">İlanınızı gördüm ve çok ilgileniyorum. Evi bu hafta içi görmek için bir randevu...</p>
<div class="mt-2 flex items-center gap-2">
<span class="bg-yellow-100 text-yellow-800 font-label-caps text-[9px] px-2 py-0.5 rounded-full">%78 Eşleşme</span>
</div>
</div>
<div class="flex items-center text-outline">
<span class="material-symbols-outlined text-[20px]">chevron_right</span>
</div>
</div>
</div>
</div>
</div>
</div>
</main>
</body></html>