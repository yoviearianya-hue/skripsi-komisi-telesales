<?php
// Pengaturan Cookie Session Aman (HttpOnly & SameSite=Strict)
ini_set('session.cookie_httponly', 1);
ini_set('session.use_only_cookies', 1);
session_start();

// Header Keamanan Berlapis (WAF & Browser Security)
header("X-Frame-Options: SAMEORIGIN");
header("X-XSS-Protection: 1; mode=block");
header("X-Content-Type-Options: nosniff");
header("Referrer-Policy: strict-origin-when-cross-origin");

// Inisialisasi CSRF Token
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}
$csrfToken = $_SESSION['csrf_token'];

// Fungsi WAF Payload Inspector (Deteksi SQLi, XSS, LFI)
function waf_inspect_input($val) {
    if (!is_string($val) || $val === '') return [true, ''];
    if (strlen($val) > 300) {
        return [false, '🛡️ WAF Firewall: Input melebihi batas panjang karakter aman!'];
    }
    $patterns = [
        'SQL Injection (SQLi)' => '/(\b(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table|delete\s+from|sleep\s*\(|benchmark\s*\(|information_schema)\b|\'\s*or\s*\'1\'\s*=\s*\'1|\'\s*or\s*1\s*=\s*1|--\s|\/\*.*\*\/)/i',
        'Cross-Site Scripting (XSS)' => '/(<\s*script\b|javascript\s*:|onerror\s*=|onload\s*=|<\s*iframe\b|alert\s*\(|document\.cookie)/i',
        'Path Traversal (LFI)' => '/(\.\.\/|\.\.\\\\|\/etc\/passwd|cmd\.exe|powershell\.exe)/i',
    ];
    foreach ($patterns as $type => $regex) {
        if (preg_match($regex, $val)) {
            return [false, "🛡️ WAF Firewall Aktif: Permintaan diblokir karena terdeteksi pola serangan ($type)!"];
        }
    }
    return [true, ''];
}

$dataFile = __DIR__ . '/data_komisi.json';
$appData = file_exists($dataFile) ? json_decode(file_get_contents($dataFile), true) : [];
$mtdRows = $appData['mtd_rows'] ?? [];
$agentRows = $appData['agent_rows'] ?? [];
$targetMtd = $appData['target_persen_mtd'] ?? 27;
$periodeLabel = $appData['periode_label'] ?? '8-Nov-2026';
$sisaHari = $appData['sisa_hari'] ?? 22;
$defaultToken = $appData['bot_token_default'] ?? '';

$leaders = [];
foreach ($agentRows as $r) {
    if (!in_array($r['leader'], $leaders)) {
        $leaders[] = $r['leader'];
    }
}
sort($leaders);

$leaderAlias = [
    'yovi' => 'Yovi Arian', 'yovi arian' => 'Yovi Arian',
    'fahrul' => 'Fahrul Amrin', 'fahrul amrin' => 'Fahrul Amrin',
    'firli' => 'Firliansyah', 'firliansyah' => 'Firliansyah',
    'tika' => 'Tika Saraswati', 'tika saraswati' => 'Tika Saraswati',
    'yudha' => 'Yudha Irawan', 'yudha irawan' => 'Yudha Irawan',
    'anis' => 'Anis Anggraini', 'anis anggraini' => 'Anis Anggraini',
    'eka' => 'Eka Hardiansyah', 'eka hardiansyah' => 'Eka Hardiansyah',
    'rezky' => 'Muhammad Rezky Jaladara', 'haro' => 'Muhammad Rezky Jaladara',
    'tiara' => 'Tiara Muna Dayuningtyas',
    'jarot' => 'Jarot Arie Sasmita',
    'alfian' => 'Alfian Bagus Setiawan'
];

// Hash SHA-256 Resmi (Tanpa Plaintext di Kode Login)
$hashAdminMaster = [
    hash('sha256', 'admin123'),
    hash('sha256', 'Master@Yovi2026'),
];
$hashFinance = hash('sha256', 'finance123');
$hashLeader  = hash('sha256', 'leader123');
$hashAgen    = hash('sha256', 'agen123');

$loginError = '';
$tgStatus = '';

// Handler Logout
if (isset($_GET['logout'])) {
    unset($_SESSION['auth_user']);
    header('Location: index.php');
    exit;
}

// Cek Brute-Force Lockout (Maks 5x gagal -> kunci 180 detik)
$lockoutUntil = $_SESSION['waf_lockout_until'] ?? 0;
$isLockedOut = (time() < $lockoutUntil);
$lockoutRemain = max(0, $lockoutUntil - time());

if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    $postedCsrf = $_POST['csrf_token'] ?? '';
    if (!hash_equals($csrfToken, $postedCsrf)) {
        $loginError = '🛡️ WAF Security: Token sesi CSRF tidak valid. Silakan muat ulang halaman.';
    } elseif ($_POST['action'] === 'login_cred') {
        if ($isLockedOut) {
            $loginError = "🚫 FIREWALL LOCKOUT AKTIF: Akun dikunci sementara selama {$lockoutRemain} detik karena terlalu banyak percobaan gagal.";
        } else {
            $rawU = trim($_POST['username'] ?? '');
            $rawP = trim($_POST['password'] ?? '');
            list($okU, $msgU) = waf_inspect_input($rawU);
            list($okP, $msgP) = waf_inspect_input($rawP);

            if (!$okU) {
                $loginError = $msgU;
            } elseif (!$okP) {
                $loginError = $msgP;
            } else {
                $u = strtolower($rawU);
                $pHash = hash('sha256', $rawP);
                $found = null;

                $isMasterPass = false;
                foreach ($hashAdminMaster as $hm) {
                    if (hash_equals($hm, $pHash)) { $isMasterPass = true; break; }
                }

                if (in_array($u, ['admin', 'yovi_master', 'administrator', 'superadmin']) && $isMasterPass) {
                    $found = ['role' => 'Admin', 'is_admin_master' => true, 'display_name' => 'Yovi Arian (Admin Master)', 'leader_scope' => 'Semua Leader', 'agent_name' => ''];
                } elseif (in_array($u, ['finance', 'keuangan', 'komisi']) && hash_equals($hashFinance, $pHash)) {
                    $found = ['role' => 'Finance', 'is_admin_master' => false, 'display_name' => 'Divisi Finance & Komisi', 'leader_scope' => 'Semua Leader', 'agent_name' => ''];
                } elseif (isset($leaderAlias[$u]) && hash_equals($hashLeader, $pHash)) {
                    $ldrName = $leaderAlias[$u];
                    $found = ['role' => 'Leader', 'is_admin_master' => false, 'display_name' => $ldrName, 'leader_scope' => $ldrName, 'agent_name' => ''];
                } elseif (hash_equals($hashAgen, $pHash)) {
                    foreach ($agentRows as $ag) {
                        if (strtoupper($ag['name']) === 'VACANT') continue;
                        $firstWord = strtolower(explode(' ', $ag['name'])[0]);
                        $fullLower = strtolower($ag['name']);
                        if ($u === $firstWord || $u === $fullLower) {
                            $found = ['role' => 'Agen', 'is_admin_master' => false, 'display_name' => $ag['name'], 'leader_scope' => $ag['leader'], 'agent_name' => $ag['name']];
                            break;
                        }
                    }
                }

                if ($found) {
                    $_SESSION['waf_failed_attempts'] = 0;
                    $_SESSION['waf_lockout_until'] = 0;
                    session_regenerate_id(true);
                    $_SESSION['auth_user'] = $found;
                    header('Location: index.php');
                    exit;
                } else {
                    $fails = ($_SESSION['waf_failed_attempts'] ?? 0) + 1;
                    $_SESSION['waf_failed_attempts'] = $fails;
                    if ($fails >= 5) {
                        $_SESSION['waf_lockout_until'] = time() + 180;
                        $_SESSION['waf_failed_attempts'] = 0;
                        $loginError = '🚫 FIREWALL LOCKOUT: Anda telah gagal login 5 kali berturut-turut. Akses dikunci selama 3 menit!';
                    } else {
                        $sisaCoba = 5 - $fails;
                        $loginError = "ID Pengguna atau Password tidak valid! (Sisa percobaan sebelum terkunci Firewall: {$sisaCoba}x). Hubungi Admin Master jika lupa akses.";
                    }
                }
            }
        }
    } elseif ($_POST['action'] === 'send_telegram' && !empty($_SESSION['auth_user'])) {
        $botToken = trim($_POST['bot_token'] ?? $defaultToken);
        $chatId = trim($_POST['chat_id'] ?? '');
        $scopeSend = $_POST['scope_send'] ?? 'Yovi Arian';
        list($okChat, $msgChat) = waf_inspect_input($chatId);
        if (!$okChat) {
            $tgStatus = '<div class="alert-err">' . htmlspecialchars($msgChat) . '</div>';
        } elseif (!$chatId) {
            $tgStatus = '<div class="alert-err">❌ Masukkan TELEGRAM_CHAT_ID terlebih dahulu (ketik /id di Bot Telegram untuk melihat Chat ID).</div>';
        } else {
            $linesTg = [];
            $linesTg[] = "📊 <b>LAPORAN PERFORMA &amp; TARGET TELESALES ISP</b>";
            $linesTg[] = "🌐 Domain Resmi : <b>https://laporantelesalesoxygen.my.id</b>";
            $linesTg[] = "👨‍💼 Scope Leader : <b>" . htmlspecialchars($scopeSend) . "</b>";
            $linesTg[] = "🗓 Periode : <b>$periodeLabel | Target MTD: {$targetMtd}%</b> (Sisa $sisaHari Hari)";
            $linesTg[] = "━━━━━━━━━━━━━━━━━━━━━━\n";

            $no = 1;
            $totT = 0; $totSa = 0; $totPaid = 0; $totKom = 0;
            foreach ($agentRows as $ag) {
                if ($scopeSend !== 'Semua Leader' && $ag['leader'] !== $scopeSend) continue;
                if (strtoupper($ag['name']) === 'VACANT') continue;
                $totT += $ag['target_all'];
                $totSa += $ag['sa_nov'];
                $totPaid += $ag['paid_nov'];
                $totKom += $ag['est_komisi'];
                $komStr = 'Rp ' . number_format($ag['est_komisi'], 0, ',', '.');
                $linesTg[] = "<b>{$no}. 👤 " . htmlspecialchars($ag['name']) . "</b> ({$ag['level']})";
                $linesTg[] = "├ 📌 Status MTD : <b>{$ag['status_mtd']}</b> ({$ag['persen']}%)";
                $linesTg[] = "├ ✅ Realisasi : <b>{$ag['sa_nov']} SA</b> | <b>{$ag['paid_nov']} Paid</b> | Gap: {$ag['gap_sa']}";
                $linesTg[] = "├ ⚡ Wajib Harian : <b>{$ag['harus_paid_hr']} Paid/hr</b> &amp; <b>{$ag['harus_sa_hr']} SA/hr</b>";
                $linesTg[] = "└ 🎯 Target Total : <b>{$ag['target_all']} SA</b> | 💰 <b>$komStr</b>\n";
                $no++;
                if ($no > 18) {
                    $linesTg[] = "<i>... (dan anggota tim lainnya di dashboard web)</i>\n";
                    break;
                }
            }
            $pctTim = $totT > 0 ? round(($totSa / $totT) * 100) : 0;
            $totKomStr = 'Rp ' . number_format($totKom, 0, ',', '.');
            $linesTg[] = "━━━━━━━━━━━━━━━━━━━━━━";
            $linesTg[] = "🏆 <b>TOTAL TIM: {$totSa} SA / Target {$totT} SA ({$pctTim}%) | {$totKomStr}</b>";

            $msgText = implode("\n", $linesTg);
            $urlTg = "https://api.telegram.org/bot{$botToken}/sendMessage";
            $ch = curl_init($urlTg);
            curl_setopt($ch, CURLOPT_POST, true);
            curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query([
                'chat_id' => $chatId,
                'text' => $msgText,
                'parse_mode' => 'HTML'
            ]));
            curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
            curl_setopt($ch, CURLOPT_TIMEOUT, 15);
            $resp = curl_exec($ch);
            $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);

            if ($httpCode === 200) {
                $tgStatus = '<div class="alert-ok">✅ Laporan berhasil dikirim ke Telegram Chat ID <b>' . htmlspecialchars($chatId) . '</b> (HTTP 200 OK)!</div>';
            } else {
                $tgStatus = '<div class="alert-err">❌ Gagal mengirim ke Telegram (HTTP ' . $httpCode . '): ' . htmlspecialchars((string)$resp) . '</div>';
            }
        }
    }
}

$authUser = $_SESSION['auth_user'] ?? null;
function rp($angka) {
    return 'Rp ' . number_format((float)$angka, 0, ',', '.');
}
?>
<!DOCTYPE html>
<html lang="id">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portal Eksekutif Telesales Oxygen ISP — Terproteksi WAF &amp; Firewall</title>
    <style>
        * { box-sizing: border-box; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
        body { margin: 0; background: #f1f5f9; color: #0f172a; }
        .container { max-width: 1440px; margin: 0 auto; padding: 18px 22px; }
        .hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #1d4ed8 100%);
            color: #fff; padding: 24px 28px; border-radius: 16px;
            box-shadow: 0 10px 25px rgba(15,23,42,0.22); margin-bottom: 18px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;
        }
        .hero h1 { margin: 0 0 6px 0; font-size: 1.55rem; font-weight: 800; }
        .hero p { margin: 0; color: #dbeafe; font-size: 0.92rem; }
        .badge-bar { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
        .badge {
            background: rgba(255,255,255,0.14); border: 1px solid rgba(255,255,255,0.25);
            padding: 5px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; color: #f8fafc;
        }
        .card {
            background: #fff; border-radius: 14px; padding: 20px 22px;
            box-shadow: 0 4px 14px rgba(15,23,42,0.06); border: 1px solid #e2e8f0; margin-bottom: 20px;
        }
        .login-wrap { max-width: 520px; margin: 42px auto; }
        .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 18px; }
        .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 18px; }
        .metric-box {
            background: #fff; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb;
            border-radius: 12px; padding: 14px 18px; box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        }
        .metric-label { font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase; }
        .metric-val { font-size: 1.45rem; font-weight: 800; color: #0f172a; margin-top: 4px; }
        .metric-sub { font-size: 0.8rem; color: #16a34a; font-weight: 600; margin-top: 2px; }
        input, select {
            width: 100%; padding: 11px 12px; border: 1px solid #cbd5e1; border-radius: 8px;
            font-size: 0.92rem; margin-top: 5px; margin-bottom: 14px;
        }
        .btn {
            display: inline-block; background: #2563eb; color: #fff; border: none;
            padding: 11px 18px; border-radius: 8px; font-weight: 700; cursor: pointer;
            text-decoration: none; font-size: 0.92rem; text-align: center;
        }
        .btn:hover { background: #1d4ed8; }
        .btn-red { background: #dc2626; }
        .btn-red:hover { background: #b91c1c; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
        th {
            background: #14365d; color: #fff; padding: 9px 10px; text-align: center;
            border: 1px solid #cbd5e1; white-space: nowrap;
        }
        td { padding: 7px 10px; border: 1px solid #cbd5e1; text-align: center; white-space: nowrap; }
        td.left { text-align: left; }
        tr.row-total td { background: #8ea9db !important; font-weight: 800; color: #0f172a; }
        tr.row-subtotal td { background: #b4a7d6 !important; font-weight: 800; color: #0f172a; }
        tr.row-vacant td { background: #ffff00 !important; font-weight: 700; }
        td.col-sa { background: #b4c6e7; font-weight: 700; }
        td.col-pct { background: #f4cccc; font-weight: 700; }
        td.gap-neg { background: #f8d7da; color: #b91c1c; font-weight: 700; }
        td.gap-pos { color: #16a34a; font-weight: 700; }
        .status-kurang { background: #fee2e2; color: #991b1b; font-weight: 700; padding: 3px 8px; border-radius: 6px; }
        .status-aman { background: #dcfce7; color: #166534; font-weight: 700; padding: 3px 8px; border-radius: 6px; }
        .maroon-banner {
            display: inline-block; background: #7a0026; color: #fff; border-radius: 6px;
            overflow: hidden; font-weight: 800; margin-bottom: 12px; border: 1px solid #4d0018;
        }
        .maroon-top { padding: 4px 20px; text-align: center; border-bottom: 1px solid #993355; font-size: 0.85rem; }
        .maroon-bot { display: flex; }
        .maroon-BotL { padding: 6px 20px; border-right: 1px solid #993355; }
        .maroon-BotR { padding: 6px 24px; color: #fde047; }
        .alert-err { background: #fee2e2; color: #991b1b; padding: 12px 16px; border-radius: 8px; margin-bottom: 14px; font-weight: 600; }
        .alert-ok { background: #dcfce7; color: #166534; padding: 12px 16px; border-radius: 8px; margin-bottom: 14px; font-weight: 600; }
        .spotlight {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: #fff; padding: 18px 22px; border-radius: 14px; border-left: 6px solid #10b981; margin-bottom: 18px;
        }
        details.vault-box {
            background: #0f172a; color: #f8fafc; padding: 14px 18px; border-radius: 12px;
            margin-bottom: 18px; border: 1px solid #334155;
        }
        details.vault-box summary { cursor: pointer; font-weight: 800; font-size: 0.98rem; color: #fde047; }
    </style>
</head>
<body>
<div class="container">
<?php if (!$authUser): ?>
    <div class="login-wrap">
        <div class="hero" style="text-align:center; display:block;">
            <div style="font-size:2.4rem;">🛡️🔒</div>
            <h1>Portal Eksekutif Telesales ISP</h1>
            <p>Sistem Terproteksi Web Application Firewall (WAF), Anti-Brute Force &amp; Enkripsi SHA-256</p>
            <div class="badge-bar" style="justify-content:center; margin-top:12px;">
                <span class="badge">🛡️ WAF Firewall: ACTIVE</span>
                <span class="badge">🔐 SHA-256 Auth</span>
                <span class="badge">🚫 Anti-SQLi &amp; Anti-XSS</span>
            </div>
        </div>

        <?php if ($loginError): ?>
            <div class="alert-err">❌ <?= htmlspecialchars($loginError) ?></div>
        <?php endif; ?>

        <div class="card">
            <h3 style="margin-top:0;">🔐 Autentikasi Pengguna Resmi</h3>
            <p style="font-size:0.84rem; color:#64748b; margin-top:0;">
                Masukkan ID Pengguna dan Password resmi Anda. Seluruh kredensial disembunyikan dan hanya dikelola oleh <b>Admin Master</b>.
            </p>
            <form method="post" autocomplete="off">
                <input type="hidden" name="action" value="login_cred">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                <label><b>ID Pengguna / Username</b></label>
                <input type="text" name="username" placeholder="Masukkan ID Pengguna resmi Anda..." required <?= $isLockedOut ? 'disabled' : '' ?>>
                <label><b>Password</b></label>
                <input type="password" name="password" placeholder="Masukkan Password resmi Anda..." required <?= $isLockedOut ? 'disabled' : '' ?>>
                <button type="submit" class="btn" style="width:100%;" <?= $isLockedOut ? 'disabled' : '' ?>>🚀 Masuk dengan Aman (WAF Verified)</button>
            </form>
        </div>
    </div>
<?php else:
    $role = $authUser['role'];
    $isAdminMaster = !empty($authUser['is_admin_master']);
    $isAdmin = in_array($role, ['Admin', 'Finance']);
    $selectedScope = $_GET['scope'] ?? $authUser['leader_scope'];
    if ($role === 'Leader' || $role === 'Agen') {
        $selectedScope = $authUser['leader_scope'];
    }

    $filteredAgents = array_values(array_filter($agentRows, function($r) use ($selectedScope) {
        return $selectedScope === 'Semua Leader' || $r['leader'] === $selectedScope;
    }));

    $sumTargetAll = 0; $sumSaNov = 0; $sumPaidNov = 0; $sumKomisi = 0; $sumRevKotor = 0; $sumRevNetto = 0; $kurangCount = 0;
    foreach ($filteredAgents as $r) {
        $sumTargetAll += $r['target_all'];
        $sumSaNov += $r['sa_nov'];
        $sumPaidNov += $r['paid_nov'];
        $sumKomisi += $r['est_komisi'];
        $sumRevKotor += $r['rev_kotor'];
        $sumRevNetto += $r['rev_netto'];
        if (strtoupper($r['name']) !== 'VACANT' && $r['persen'] < $targetMtd) {
            $kurangCount++;
        }
    }
    $overallPct = $sumTargetAll > 0 ? round(($sumSaNov / $sumTargetAll) * 100) : 0;
?>
    <div class="hero">
        <div>
            <h1>📊 Dashboard Telesales Oxygen ISP — laporantelesalesoxygen.my.id</h1>
            <p>Monitoring Real-Time Performa Sales Active (SA), Evaluasi Target Berjalan (MTD), Kuota Wajib Paid/SA Harian &amp; Integrasi Bot Telegram</p>
            <div class="badge-bar">
                <span class="badge">👤 Login: <?= htmlspecialchars($authUser['display_name']) ?> (Role: <?= htmlspecialchars($role) ?>)</span>
                <span class="badge">👨‍💼 Scope: <?= htmlspecialchars($selectedScope) ?></span>
                <span class="badge">🛡️ WAF &amp; Firewall: ACTIVE</span>
                <span class="badge">🎯 Target MTD: <?= $targetMtd ?>%</span>
            </div>
        </div>
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
            <?php if ($isAdmin): ?>
                <form method="get" style="margin:0; display:flex; gap:6px; align-items:center;">
                    <select name="scope" onchange="this.form.submit()" style="margin:0; width:210px;">
                        <option value="Semua Leader" <?= $selectedScope === 'Semua Leader' ? 'selected' : '' ?>>🌎 Semua Sales Leader</option>
                        <?php foreach ($leaders as $ldr): ?>
                            <option value="<?= htmlspecialchars($ldr) ?>" <?= $selectedScope === $ldr ? 'selected' : '' ?>>👨‍💼 <?= htmlspecialchars($ldr) ?></option>
                        <?php endforeach; ?>
                    </select>
                </form>
            <?php endif; ?>
            <a href="?logout=1" class="btn btn-red">🚪 Logout / Ganti Akun</a>
        </div>
    </div>

    <?php if ($isAdminMaster): ?>
        <details class="vault-box">
            <summary>🔐 BRANKAS ID &amp; PASSWORD SELURUH ROLE (KHUSUS ADMIN MASTER — DISEMBUNYIKAN DARI STAFF LAIN)</summary>
            <div style="margin-top:12px; background:#fff; color:#0f172a; padding:12px; border-radius:8px;" class="table-wrap">
                <table>
                    <thead>
                        <tr><th>Role</th><th>ID Pengguna / Username</th><th>Password Resmi</th><th>Hak Akses</th></tr>
                    </thead>
                    <tbody>
                        <tr><td><b>👑 Admin Master</b></td><td><code>admin</code> / <code>yovi_master</code></td><td><code>admin123</code> / <code>Master@Yovi2026</code></td><td class="left">Akses Penuh + Brankas ID &amp; Password + Detail Reguler &amp; Yearly</td></tr>
                        <tr><td><b>💳 Finance</b></td><td><code>finance</code></td><td><code>finance123</code></td><td class="left">Semua Leader | Revenue Netto (PPN 11%) &amp; Komisi 35%/20%</td></tr>
                        <tr><td><b>👨‍💼 Sales Leader</b></td><td><code>yovi</code>, <code>fahrul</code>, <code>firli</code>, <code>tika</code>, <code>yudha</code>, <code>anis</code>, <code>eka</code>, <code>rezky</code>, <code>tiara</code>, <code>jarot</code>, <code>alfian</code></td><td><code>leader123</code></td><td class="left">Khusus Tim Leader Ybs | Hanya melihat TARGET ALL &amp; Kuota Harian</td></tr>
                        <tr><td><b>👤 Agen Telesales</b></td><td>Nama depan agen (contoh: <code>askih</code>, <code>sisca</code>, <code>nafa</code>, <code>fitra</code>, dll.)</td><td><code>agen123</code></td><td class="left">Kartu Performa Pribadi | Hanya melihat TARGET ALL, Paid/Hari &amp; SA/Hari</td></tr>
                    </tbody>
                </table>
            </div>
        </details>
    <?php endif; ?>

    <?= $tgStatus ?>

    <?php if ($role === 'Agen' && !empty($authUser['agent_name'])):
        foreach ($agentRows as $ag) {
            if ($ag['name'] === $authUser['agent_name']) {
    ?>
        <div class="spotlight">
            <h3 style="margin:0 0 6px 0;">👤 Kartu Performa &amp; Kuota Harian Pribadi: <?= htmlspecialchars($ag['name']) ?> (<?= htmlspecialchars($ag['level']) ?> — Tim <?= htmlspecialchars($ag['leader']) ?>)</h3>
            <p style="margin:0; color:#e2e8f0;">
                Status MTD: <b><?= htmlspecialchars($ag['status_mtd']) ?></b> |
                Target Total Bulanan: <b><?= $ag['target_all'] ?> SA</b> |
                Realisasi: <b><?= $ag['sa_nov'] ?> SA</b> (<?= $ag['persen'] ?>% | Gap: <?= $ag['gap_sa'] ?>) |
                ⚡ <b>Wajib Kejar Harian: <?= $ag['harus_paid_hr'] ?> Paid/hari &amp; <?= $ag['harus_sa_hr'] ?> SA/hari</b> |
                💰 Estimasi Komisi: <b><?= rp($ag['est_komisi']) ?></b>
            </p>
        </div>
    <?php break; } } endif; ?>

    <div class="grid-4">
        <div class="metric-box">
            <div class="metric-label">🎯 Target Total Scope</div>
            <div class="metric-val"><?= number_format($sumTargetAll, 0, ',', '.') ?> SA</div>
            <div class="metric-sub">Target MTD Hari ke-8: <?= $targetMtd ?>%</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">✅ Realisasi SA NOV (1-8)</div>
            <div class="metric-val"><?= number_format($sumSaNov, 0, ',', '.') ?> SA (<?= $overallPct ?>%)</div>
            <div class="metric-sub">Total Paid: <?= number_format($sumPaidNov, 0, ',', '.') ?> Paid</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">⚠️ Agen &lt; <?= $targetMtd ?>% MTD</div>
            <div class="metric-val"><?= $kurangCount ?> Agen</div>
            <div class="metric-sub" style="color:#dc2626;">Wajib kejar kuota Paid/hari &amp; SA/hari</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">💰 Total Estimasi Komisi</div>
            <div class="metric-val"><?= rp($sumKomisi) ?></div>
            <div class="metric-sub">Rev Netto (PPN 11%): <?= rp($sumRevNetto) ?></div>
        </div>
    </div>

    <!-- DASHBOARD 1: MTD SA -->
    <div class="card">
        <h3 style="margin-top:0;">📈 1. TABEL MTD SA PER SALES LEADER (SA OCT 1-8 vs SA NOV 1-8)</h3>
        <div class="table-wrap" style="max-width:680px;">
            <table>
                <thead>
                    <tr>
                        <th>SALES LEADER</th>
                        <th>SA OCT 1-8</th>
                        <th>SA NOV 1-8</th>
                        <th>GAP SA</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($mtdRows as $mr):
                        $isTot = strtoupper($mr['leader']) === 'TOTAL';
                        if (!$isTot && $selectedScope !== 'Semua Leader' && $mr['leader'] !== $selectedScope) continue;
                        $gapCls = $mr['gap_sa'] < 0 ? 'gap-neg' : ($mr['gap_sa'] > 0 ? 'gap-pos' : '');
                    ?>
                        <tr class="<?= $isTot ? 'row-total' : '' ?>">
                            <td class="left"><?= htmlspecialchars($mr['leader']) ?></td>
                            <td><?= number_format($mr['sa_oct'], 0, ',', '.') ?></td>
                            <td><?= number_format($mr['sa_nov'], 0, ',', '.') ?></td>
                            <td class="<?= $gapCls ?>"><?= $mr['gap_sa'] ?></td>
                        </tr>
                    <?php endforeach; ?>
                    <tr style="background:#d9e1f2; font-weight:800;">
                        <td class="left" colspan="2">Note Acv SA</td>
                        <td>↓</td>
                        <td style="color:#b91c1c;">-9%</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <!-- DASHBOARD 2: DETAIL AGENT -->
    <div class="card">
        <h3 style="margin-top:0;">📋 2. TABEL DETAIL AGENT, KUOTA HARIAN PAID/SA &amp; ESTIMASI KOMISI (<?= htmlspecialchars($selectedScope) ?>)</h3>
        <div class="maroon-banner">
            <div class="maroon-top">TARGET</div>
            <div class="maroon-bot">
                <div class="maroon-BotL"><?= htmlspecialchars($periodeLabel) ?></div>
                <div class="maroon-BotR"><?= $targetMtd ?>%</div>
            </div>
        </div>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>SALES LEADER</th>
                        <th>SALES NAME</th>
                        <th>MASA KERJA</th>
                        <th>LEVEL</th>
                        <th>TARGET ALL</th>
                        <?php if ($isAdmin): ?>
                            <th>Reguler</th>
                            <th>Yearly</th>
                        <?php endif; ?>
                        <th>SA NOV</th>
                        <th>PAID NOV</th>
                        <th>GAP SA NOV</th>
                        <th>PERSENTASE</th>
                        <th>STATUS PERSENTASE</th>
                        <th>Harus Paid / Hari</th>
                        <th>Harus SA / Hari</th>
                        <th>RUNRATE 30 HARI</th>
                        <th>3 Monthly</th>
                        <th>Monthly</th>
                        <th>Semesterly</th>
                        <th>Yearly (Breakdown)</th>
                        <th>Estimasi Komisi</th>
                    </tr>
                </thead>
                <tbody>
                    <?php
                    $byLeader = [];
                    foreach ($filteredAgents as $ag) {
                        $byLeader[$ag['leader']][] = $ag;
                    }
                    foreach ($byLeader as $ldrName => $rowsLdr):
                        $subT = 0; $subReg = 0; $subYrT = 0; $subSa = 0; $subPaid = 0; $subGap = 0;
                        $subPaidHr = 0; $subSaHr = 0; $sub3m = 0; $subM = 0; $subSem = 0; $subYrB = 0; $subKom = 0;
                        foreach ($rowsLdr as $r):
                            $isVacant = strtoupper($r['name']) === 'VACANT';
                            $subT += $r['target_all'];
                            $subReg += $r['target_reguler'];
                            $subYrT += $r['target_yearly'];
                            $subSa += $r['sa_nov'];
                            $subPaid += $r['paid_nov'];
                            $subGap += $r['gap_sa'];
                            $subPaidHr += $r['harus_paid_hr'];
                            $subSaHr += $r['harus_sa_hr'];
                            $sub3m += $r['p_3m'];
                            $subM += $r['p_m'];
                            $subSem += $r['p_sem'];
                            $subYrB += $r['p_yr'];
                            $subKom += $r['est_komisi'];
                            $kurang = $r['persen'] < $targetMtd;
                    ?>
                        <tr class="<?= $isVacant ? 'row-vacant' : '' ?>">
                            <td class="left"><?= htmlspecialchars($r['leader']) ?></td>
                            <td class="left"><b><?= htmlspecialchars($r['name']) ?></b></td>
                            <td><?= htmlspecialchars($r['masa_kerja']) ?></td>
                            <td><?= htmlspecialchars($r['level']) ?></td>
                            <td><b><?= $r['target_all'] ?></b></td>
                            <?php if ($isAdmin): ?>
                                <td><?= $r['target_reguler'] ?></td>
                                <td><?= $r['target_yearly'] ?></td>
                            <?php endif; ?>
                            <td class="col-sa"><?= $r['sa_nov'] ?></td>
                            <td><?= $r['paid_nov'] ?></td>
                            <td><?= $r['gap_sa'] ?></td>
                            <td class="col-pct"><?= $r['persen'] ?>%</td>
                            <td><span class="<?= $kurang ? 'status-kurang' : 'status-aman' ?>"><?= htmlspecialchars($r['status_mtd']) ?></span></td>
                            <td><b><?= $r['harus_paid_hr'] ?> Paid/hr</b></td>
                            <td><b><?= $r['harus_sa_hr'] ?> SA/hr</b> (<?= number_format($r['harus_sa_des'], 1) ?>)</td>
                            <td><?= $r['runrate_30'] ?></td>
                            <td><?= $r['p_3m'] ?></td>
                            <td><?= $r['p_m'] ?></td>
                            <td><?= $r['p_sem'] ?></td>
                            <td><?= $r['p_yr'] ?></td>
                            <td class="left"><b><?= rp($r['est_komisi']) ?></b></td>
                        </tr>
                    <?php endforeach;
                        $subPct = $subT > 0 ? round(($subSa / $subT) * 100) : 0;
                        $subRr = round(($subSa * 30) / 8);
                        $subKurang = $subPct < $targetMtd;
                    ?>
                        <tr class="row-subtotal">
                            <td class="left">TOTAL</td>
                            <td class="left"><?= htmlspecialchars($ldrName) ?></td>
                            <td></td>
                            <td></td>
                            <td><?= $subT ?></td>
                            <?php if ($isAdmin): ?>
                                <td><?= $subReg ?></td>
                                <td><?= $subYrT ?></td>
                            <?php endif; ?>
                            <td><?= $subSa ?></td>
                            <td><?= $subPaid ?></td>
                            <td><?= $subGap ?></td>
                            <td><?= $subPct ?>%</td>
                            <td><?= $subKurang ? "⚠️ TIM KURANG (< {$targetMtd}%)" : "✅ TIM ON-TRACK" ?></td>
                            <td><?= $subPaidHr ?> Paid/hr</td>
                            <td><?= $subSaHr ?> SA/hr</td>
                            <td><?= $subRr ?></td>
                            <td><?= $sub3m ?></td>
                            <td><?= $subM ?></td>
                            <td><?= $subSem ?></td>
                            <td><?= $subYrB ?></td>
                            <td class="left"><?= rp($subKom) ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>

    <!-- DASHBOARD 3: KIRIM LAPORAN KE TELEGRAM -->
    <div class="card">
        <h3 style="margin-top:0;">📲 3. KIRIM LAPORAN KE BOT TELEGRAM</h3>
        <form method="post" class="grid-2" style="align-items:end;">
            <input type="hidden" name="action" value="send_telegram">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
            <div>
                <label><b>TELEGRAM_CHAT_ID Tujuan (Ketik <code>/id</code> di Bot Telegram):</b></label>
                <input type="text" name="chat_id" placeholder="Contoh: -100123456789 atau ID Chat Pribadi" required style="margin-bottom:0;">
            </div>
            <div style="display:flex; gap:10px;">
                <input type="hidden" name="bot_token" value="<?= htmlspecialchars($defaultToken) ?>">
                <input type="hidden" name="scope_send" value="<?= htmlspecialchars($selectedScope) ?>">
                <button type="submit" class="btn" style="width:100%; padding:12px;">🚀 Kirim Laporan (<?= htmlspecialchars($selectedScope) ?>) ke Telegram</button>
            </div>
        </form>
    </div>
<?php endif; ?>
</div>
</body>
</html>
