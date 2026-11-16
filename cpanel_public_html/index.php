<?php
// ============================================================================
// PORTAL EKSEKUTIF TELESALES OXYGEN ISP — laporantelesalesoxygen.my.id
// Mandiri 100% di Server cPanel PHP (Tanpa Docker), Terproteksi WAF Berlapis
// ============================================================================
$isHttps = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') || (($_SERVER['SERVER_PORT'] ?? '') == 443);
ini_set('session.cookie_httponly', '1');
ini_set('session.use_only_cookies', '1');
if (PHP_VERSION_ID >= 70300) {
    session_set_cookie_params([
        'lifetime' => 0,
        'path'     => '/',
        'secure'   => $isHttps,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
}
@ini_set('memory_limit', '512M');
@set_time_limit(300);
session_start();

define('APP_BOOT', true);
require_once __DIR__ . '/engine.php';

// Security Headers Berlapis
header("X-Frame-Options: SAMEORIGIN");
header("X-XSS-Protection: 1; mode=block");
header("X-Content-Type-Options: nosniff");
header("Referrer-Policy: strict-origin-when-cross-origin");
header("Permissions-Policy: geolocation=(), microphone=(), camera=()");
header("Content-Security-Policy: frame-ancestors 'self';");

if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}
$csrfToken = $_SESSION['csrf_token'];

$uploadsDir = __DIR__ . '/uploads';
if (!is_dir($uploadsDir)) {
    @mkdir($uploadsDir, 0755, true);
}

$dataFile            = __DIR__ . '/data_komisi.json';
$defaultDataFile     = $uploadsDir . '/default_data_komisi.json';
$targetActiveFile    = $uploadsDir . '/target_active.xlsx';
$targetDefaultFile   = $uploadsDir . '/default_target.xlsx';
$poolActiveFile      = $uploadsDir . '/prospect_pool.json.gz';
$poolDefaultFile     = $uploadsDir . '/default_prospect_pool.json.gz';
$superAdminStoreFile = $uploadsDir . '/superadmin_store.json';
$rolesStoreFile      = $uploadsDir . '/roles_store.json';
$rateLimitFile       = $uploadsDir . '/.waf_ratelimit.json';
$auditLogFile        = $uploadsDir . '/security_audit.log';

// Fallback Config Super Admin (PBKDF2 Hash — Tanpa Plaintext)
$superAdminFallback = [
    'username'   => 'sa_yovi_2026',
    'salt'       => '0e874ee75c9fb45738f1dc1929aa237d',
    'iterations' => 200000,
    'hash'       => '774b1c27740d2ef6112a79c86bbb81b7eda1ac8333725a835188448e4c24a434',
];

function load_json_safe(string $path, array $fallback = []): array {
    if (!file_exists($path)) return $fallback;
    $raw = @file_get_contents($path);
    $dec = $raw !== false ? json_decode($raw, true) : null;
    return is_array($dec) ? $dec : $fallback;
}

function get_superadmin_cfg(string $storeFile, array $fallback): array {
    $cfg = load_json_safe($storeFile, []);
    if (!empty($cfg['username']) && !empty($cfg['salt']) && !empty($cfg['hash'])) {
        return $cfg;
    }
    return $fallback;
}

function get_roles_cfg(string $storeFile): array {
    return load_json_safe($storeFile, []);
}

function client_ip_hash(): string {
    $ip = $_SERVER['HTTP_CF_CONNECTING_IP'] ?? $_SERVER['REMOTE_ADDR'] ?? '0.0.0.0';
    return hash('sha256', (string)$ip . '|oxygen_waf_2026');
}

function waf_log_event(string $logFile, string $category, string $user, string $msg): void {
    $u = substr(preg_replace('/[\r\n\t]/', ' ', $user ?: '-'), 0, 50);
    $m = substr(preg_replace('/[\r\n\t]/', ' ', $msg ?: '-'), 0, 220);
    $line = '[' . date('Y-m-d H:i:s') . "] [{$category}] user={$u} | {$m}\n";
    @file_put_contents($logFile, $line, FILE_APPEND | LOCK_EX);
}

function waf_read_logs(string $logFile, int $limit = 20): array {
    if (!file_exists($logFile)) {
        return ['[INFO] WAF Firewall & Audit Log Aktif di Server.'];
    }
    $lines = @file($logFile, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES);
    if (!$lines) return ['[INFO] Belum ada aktivitas tercatat.'];
    return array_reverse(array_slice($lines, -$limit));
}

function waf_inspect_input($val, string $logFile = ''): array {
    if (!is_string($val) || $val === '') return [true, ''];
    if (strlen($val) > 400) {
        if ($logFile) waf_log_event($logFile, 'WAF-BLOCK', '-', 'Payload melebihi batas panjang karakter');
        return [false, '🛡️ WAF Firewall: Input melebihi batas panjang karakter aman!'];
    }
    $patterns = [
        'SQL Injection (SQLi)' => '/(\b(union\s+select|select\s+.*\s+from|insert\s+into|drop\s+table|delete\s+from|sleep\s*\(|benchmark\s*\(|information_schema)\b|\'\s*or\s*\'1\'\s*=\s*\'1|\'\s*or\s*1\s*=\s*1|--\s|\/\*.*\*\/)/i',
        'Cross-Site Scripting (XSS)' => '/(<\s*script\b|javascript\s*:|onerror\s*=|onload\s*=|<\s*iframe\b|alert\s*\(|document\.cookie)/i',
        'Path Traversal (LFI)' => '/(\.\.\/|\.\.\\\\|\/etc\/passwd|cmd\.exe|powershell\.exe)/i',
    ];
    foreach ($patterns as $type => $regex) {
        if (preg_match($regex, $val)) {
            if ($logFile) waf_log_event($logFile, 'WAF-BLOCK', '-', "Serangan {$type}: " . substr($val, 0, 60));
            return [false, "🛡️ WAF Firewall Aktif: Permintaan diblokir karena terdeteksi pola serangan ($type)!"];
        }
    }
    return [true, ''];
}

function rate_limit_status(string $rateFile): array {
    $ipKey = client_ip_hash();
    $now = time();
    $sessUntil = (int)($_SESSION['waf_lockout_until'] ?? 0);
    $data = load_json_safe($rateFile, []);
    $rec = $data[$ipKey] ?? ['fails' => 0, 'until' => 0];
    $until = max($sessUntil, (int)($rec['until'] ?? 0));
    if ($now < $until) {
        return [true, $until - $now];
    }
    return [false, 0];
}

function rate_limit_fail(string $rateFile, string $logFile, string $u): array {
    $ipKey = client_ip_hash();
    $now = time();
    $data = load_json_safe($rateFile, []);
    // Bersihkan entri kedaluwarsa (> 1 jam)
    foreach ($data as $k => $v) {
        if (($v['ts'] ?? 0) < $now - 3600) unset($data[$k]);
    }
    $rec = $data[$ipKey] ?? ['fails' => 0, 'until' => 0, 'ts' => $now];
    $fails = max((int)($_SESSION['waf_failed_attempts'] ?? 0), (int)$rec['fails']) + 1;
    $_SESSION['waf_failed_attempts'] = $fails;
    $locked = false;
    if ($fails >= 5) {
        $until = $now + 180;
        $_SESSION['waf_lockout_until'] = $until;
        $_SESSION['waf_failed_attempts'] = 0;
        $data[$ipKey] = ['fails' => 0, 'until' => $until, 'ts' => $now];
        $locked = true;
        waf_log_event($logFile, 'BRUTE-FORCE-LOCKOUT', $u, 'IP/Sesi dikunci 180 detik setelah 5x gagal');
    } else {
        $data[$ipKey] = ['fails' => $fails, 'until' => 0, 'ts' => $now];
        waf_log_event($logFile, 'AUTH-FAIL', $u, "Gagal login ke-{$fails}/5");
    }
    @file_put_contents($rateFile, json_encode($data), LOCK_EX);
    return [$fails, $locked];
}

function rate_limit_clear(string $rateFile): void {
    $_SESSION['waf_failed_attempts'] = 0;
    $_SESSION['waf_lockout_until'] = 0;
    $ipKey = client_ip_hash();
    $data = load_json_safe($rateFile, []);
    if (isset($data[$ipKey])) {
        unset($data[$ipKey]);
        @file_put_contents($rateFile, json_encode($data), LOCK_EX);
    }
}

function is_blocked_legacy_cred(string $u, string $p): bool {
    $oldUsers = ['admin', 'administrator', 'root', 'superadmin', 'yovi_master', 'superadmin.yovi', 'finance', 'keuangan', 'komisi'];
    $oldPass = ['admin123', 'Master@Yovi2026', 'Yovi#SuperAdmin2026!', 'finance123', 'leader123', 'agen123'];
    return in_array($u, $oldUsers, true) || in_array($p, $oldPass, true);
}

function verify_super_admin_cfg(string $uInput, string $pInput, array $cfg): bool {
    $u = strtolower(trim($uInput));
    $p = trim($pInput);
    if ($u === '' || $p === '' || is_blocked_legacy_cred($u, $p)) return false;
    $uOk = hash_equals(strtolower(trim((string)$cfg['username'])), $u);
    $calc = hash_pbkdf2('sha256', $p, (string)$cfg['salt'], (int)$cfg['iterations'], 64, false);
    return $uOk && hash_equals((string)$cfg['hash'], $calc);
}

function authenticate_user(string $rawU, string $rawP, array $saCfg, array $rolesCfg): ?array {
    $u = strtolower(trim($rawU));
    $p = trim($rawP);
    if ($u === '' || $p === '' || is_blocked_legacy_cred($u, $p)) {
        return null;
    }

    // 1. Cek Super Admin (PBKDF2-HMAC-SHA256)
    if (verify_super_admin_cfg($u, $p, $saCfg)) {
        return [
            'role'            => 'Admin',
            'is_admin_master' => true,
            'username'        => $u,
            'display_name'    => 'Yovi Arian (Super Admin)',
            'leader_scope'    => 'Semua Leader',
            'agent_name'      => '',
            'agent_key'       => '',
        ];
    }

    $pHash = hash('sha256', $p);

    // 2. Cek Finance
    $fin = $rolesCfg['finance'] ?? [];
    if (!empty($fin['username']) && !empty($fin['hash'])) {
        if (hash_equals(strtolower((string)$fin['username']), $u) && hash_equals((string)$fin['hash'], $pHash)) {
            return [
                'role'            => 'Finance',
                'is_admin_master' => false,
                'username'        => $u,
                'display_name'    => 'Divisi Finance & Komisi',
                'leader_scope'    => 'Semua Leader',
                'agent_name'      => '',
                'agent_key'       => '',
            ];
        }
    }

    // 3. Cek Sales Leader
    $leaders = $rolesCfg['leaders'] ?? [];
    if (isset($leaders[$u]) && is_array($leaders[$u])) {
        $ldrHash = (string)($leaders[$u]['hash'] ?? ($rolesCfg['leader_default_hash'] ?? ''));
        if ($ldrHash !== '' && hash_equals($ldrHash, $pHash)) {
            $ldrName = (string)$leaders[$u]['leader'];
            return [
                'role'            => 'Leader',
                'is_admin_master' => false,
                'username'        => $u,
                'display_name'    => $ldrName,
                'leader_scope'    => $ldrName,
                'agent_name'      => '',
                'agent_key'       => '',
            ];
        }
    }

    // 4. Cek Agen Telesales (ID Unik `agt_*`)
    $agens = $rolesCfg['agen_accounts'] ?? [];
    if (isset($agens[$u]) && is_array($agens[$u])) {
        $agHash = (string)($agens[$u]['hash'] ?? ($rolesCfg['agen_default_hash'] ?? ''));
        if ($agHash !== '' && hash_equals($agHash, $pHash)) {
            return [
                'role'            => 'Agen',
                'is_admin_master' => false,
                'username'        => $u,
                'display_name'    => (string)$agens[$u]['name'],
                'leader_scope'    => (string)$agens[$u]['leader'],
                'agent_name'      => (string)$agens[$u]['name'],
                'agent_key'       => (string)($agens[$u]['agent_key'] ?? ''),
            ];
        }
    }

    return null;
}

function load_prospect_pool(string $poolActive, string $poolDefault): array {
    $src = file_exists($poolActive) ? $poolActive : (file_exists($poolDefault) ? $poolDefault : '');
    if ($src === '') return [];
    $gz = @file_get_contents($src);
    $raw = $gz !== false ? @gzdecode($gz) : false;
    if ($raw === false) return [];
    $dec = json_decode($raw, true);
    return is_array($dec) ? $dec : [];
}

function rp($angka): string {
    return 'Rp ' . number_format((float)$angka, 0, ',', '.');
}

// Muat Konfigurasi Awal
$saCfg    = get_superadmin_cfg($superAdminStoreFile, $superAdminFallback);
$rolesCfg = get_roles_cfg($rolesStoreFile);
$appData  = load_json_safe($dataFile, []);

$loginError   = '';
$actionStatus = '';
$tgStatus     = '';

// ============================================================================
// ENDPOINT API SYNC LANGSUNG KE SERVER (TANPA DOCKER, AUTH SUPER ADMIN)
// ============================================================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'api_sync') {
    header('Content-Type: application/json; charset=utf-8');
    list($locked, $remain) = rate_limit_status($rateLimitFile);
    if ($locked) {
        http_response_code(429);
        echo json_encode(['ok' => false, 'error' => "Lockout aktif {$remain}s"]);
        exit;
    }
    $apiU = trim((string)($_POST['api_user'] ?? ''));
    $apiP = trim((string)($_POST['api_pass'] ?? ''));
    if (!verify_super_admin_cfg($apiU, $apiP, $saCfg)) {
        rate_limit_fail($rateLimitFile, $auditLogFile, $apiU ?: 'api_sync');
        http_response_code(403);
        echo json_encode(['ok' => false, 'error' => 'Autentikasi Super Admin gagal']);
        exit;
    }
    rate_limit_clear($rateLimitFile);
    try {
        $sheetIn = trim((string)($_POST['sheet_name'] ?? ($appData['params']['sheet'] ?? "NOVEMBER'26")));
        $bLalu   = max(1, min(12, (int)($_POST['bulan_lalu'] ?? ($appData['params']['bulan_lalu'] ?? 10))));
        $bIni    = max(1, min(12, (int)($_POST['bulan_ini'] ?? ($appData['params']['bulan_ini'] ?? 11))));
        $thn     = max(2020, min(2035, (int)($_POST['tahun'] ?? ($appData['params']['tahun'] ?? 2026))));
        $tHari   = max(1, min(31, (int)($_POST['total_hari'] ?? ($appData['params']['total_hari'] ?? 30))));
        $hJalan  = max(1, min($tHari, (int)($_POST['hari_berjalan'] ?? ($appData['params']['hari_berjalan'] ?? 15))));
        $hHarian = max(1, min(31, (int)($_POST['hari_harian'] ?? $hJalan)));
        $rasio   = max(0.5, min(5.0, (float)($_POST['rasio_paid'] ?? ($appData['params']['rasio_paid'] ?? 1.25))));
        $modeP   = ($_POST['mode_prospect'] ?? 'merge') === 'replace' ? 'replace' : 'merge';

        $targetNama = $appData['sumber']['target'] ?? 'TARGET PER MONTH.xlsx';
        if (!empty($_FILES['file_target']['name']) && $_FILES['file_target']['error'] === UPLOAD_ERR_OK) {
            $origT = basename((string)$_FILES['file_target']['name']);
            if (strtolower(pathinfo($origT, PATHINFO_EXTENSION)) !== 'xlsx') {
                throw new RuntimeException('File Target harus .xlsx');
            }
            if (!move_uploaded_file($_FILES['file_target']['tmp_name'], $targetActiveFile)) {
                throw new RuntimeException('Gagal menyimpan target_active.xlsx');
            }
            $targetNama = $origT;
        }
        if (!file_exists($targetActiveFile) && file_exists($targetDefaultFile)) {
            @copy($targetDefaultFile, $targetActiveFile);
        }

        $uploadedProspects = [];
        $tmpClean = [];
        if (!empty($_FILES['file_prospect']['name'])) {
            $names = (array)$_FILES['file_prospect']['name'];
            $tmps  = (array)$_FILES['file_prospect']['tmp_name'];
            $errs  = (array)$_FILES['file_prospect']['error'];
            for ($i = 0; $i < count($names); $i++) {
                if (empty($names[$i]) || $errs[$i] !== UPLOAD_ERR_OK) continue;
                $origP = basename((string)$names[$i]);
                $extP = strtolower(pathinfo($origP, PATHINFO_EXTENSION));
                if (!in_array($extP, ['xls', 'xlsx', 'csv', 'tsv', 'html', 'htm'], true)) {
                    throw new RuntimeException("Format prospect '$origP' tidak didukung");
                }
                $dst = $uploadsDir . '/tmp_sync_' . time() . '_' . $i . '.' . $extP;
                if (move_uploaded_file($tmps[$i], $dst)) {
                    $uploadedProspects[] = ['path' => $dst, 'name' => $origP];
                    $tmpClean[] = $dst;
                }
            }
        }
        $poolAwal = ($modeP === 'merge' || empty($uploadedProspects)) ? load_prospect_pool($poolActiveFile, $poolDefaultFile) : [];
        if (empty($poolAwal) && empty($uploadedProspects)) {
            throw new RuntimeException('Tidak ada data prospect yang dapat diproses');
        }

        $hasil = proses_data([
            'target_path'        => $targetActiveFile,
            'target_name'        => $targetNama,
            'sheet'              => $sheetIn,
            'prospect_rows_awal' => $poolAwal,
            'prospects'          => $uploadedProspects,
            'bulan_lalu'         => $bLalu,
            'bulan_ini'          => $bIni,
            'tahun'              => $thn,
            'total_hari'         => $tHari,
            'hari_berjalan'      => $hJalan,
            'hari_harian'        => $hHarian,
            'rasio_paid'         => $rasio,
            'simpan_pool_path'   => $poolActiveFile,
        ]);
        foreach ($tmpClean as $tf) @unlink($tf);

        $hasil['bot_token_default'] = $appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs';
        $hasil['docker_tunnel_url'] = $appData['docker_tunnel_url'] ?? '';
        $hasil['sumber']['updated_at'] = date('Y-m-d H:i:s');
        $hasil['sumber']['updated_by'] = $apiU . ' (Auto-Sync Server)';
        file_put_contents($dataFile, json_encode($hasil, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
        waf_log_event($auditLogFile, 'SERVER-SYNC', $apiU, 'Update via Auto-Sync (' . ($hasil['sumber']['total_baris_prospect'] ?? 0) . ' baris)');

        echo json_encode([
            'ok' => true,
            'periode' => $hasil['periode_label'],
            'daily_label' => $hasil['daily_prod_date_label'] ?? '',
            'total_prospect' => $hasil['sumber']['total_baris_prospect'] ?? 0,
            'total_agent' => count($hasil['agent_rows'] ?? []),
        ]);
    } catch (Throwable $e) {
        http_response_code(400);
        echo json_encode(['ok' => false, 'error' => $e->getMessage()]);
    }
    exit;
}

// ============================================================================
// HANDLER DOWNLOAD LAPORAN EXCEL (.XLS) & CSV LANGSUNG DARI SERVER
// ============================================================================
if (isset($_GET['download']) && !empty($_SESSION['auth_user'])) {
    $dlType = $_GET['download'];
    $authU = $_SESSION['auth_user'];
    $dlScope = $_GET['scope'] ?? $authU['leader_scope'];
    if (in_array($authU['role'], ['Leader', 'Agen'], true)) {
        $dlScope = $authU['leader_scope'];
    }
    $dlAdmin = in_array($authU['role'], ['Admin', 'Finance'], true);
    $dlAgents = array_values(array_filter($appData['agent_rows'] ?? [], fn($r) => $dlScope === 'Semua Leader' || $r['leader'] === $dlScope));
    $safeName = preg_replace('/[^A-Za-z0-9_]/', '_', $dlScope);
    $lblP = preg_replace('/[^A-Za-z0-9\-]/', '_', (string)($appData['periode_label'] ?? 'Laporan'));

    if ($dlType === 'csv') {
        header('Content-Type: text/csv; charset=utf-8');
        header("Content-Disposition: attachment; filename=\"Laporan_Telesales_{$safeName}_{$lblP}.csv\"");
        $out = fopen('php://output', 'w');
        fwrite($out, "\xEF\xBB\xBF");
        $hdr = ['SALES LEADER', 'SALES NAME', 'MASA KERJA', 'LEVEL', 'TARGET ALL'];
        if ($dlAdmin) { $hdr[] = 'Reguler'; $hdr[] = 'Yearly'; }
        array_push($hdr, 'SA', 'PAID', 'SO', 'GAP SA', 'PERSENTASE', 'STATUS MTD', 'Harus Paid / Hari', 'Harus SA / Hari', 'RUNRATE', '3 Monthly', 'Monthly', 'Semesterly', 'Yearly', 'Estimasi Komisi');
        fputcsv($out, $hdr);
        foreach ($dlAgents as $r) {
            $row = [$r['leader'], $r['name'], $r['masa_kerja'], $r['level'], $r['target_all']];
            if ($dlAdmin) { $row[] = $r['target_reguler']; $row[] = $r['target_yearly']; }
            array_push($row, $r['sa_nov'], $r['paid_nov'], $r['so_nov'], $r['gap_sa'], $r['persen'] . '%', $r['status_mtd'], $r['harus_paid_hr'], $r['harus_sa_hr'], $r['runrate_30'], $r['p_3m'], $r['p_m'], $r['p_sem'], $r['p_yr'], $r['est_komisi']);
            fputcsv($out, $row);
        }
        fclose($out);
        exit;
    }
    if ($dlType === 'excel') {
        header('Content-Type: application/vnd.ms-excel; charset=utf-8');
        header("Content-Disposition: attachment; filename=\"Laporan_Lengkap_Telesales_{$safeName}_{$lblP}.xls\"");
        echo '<html><meta charset="UTF-8"><body>';
        echo '<h3>1. REKAP HARIAN (' . htmlspecialchars($appData['daily_prod_date_label'] ?? '') . ') & JUMLAH AGENT BLM PRODUKTIF</h3><table border="1"><tr><th>Sales Leader</th><th>SO</th><th>PAID</th><th>SA</th><th>Blm Produktif SO</th><th>Blm Produktif PAID</th><th>Blm Produktif SA</th></tr>';
        foreach (($appData['daily_prod_rows'] ?? []) as $dr) {
            if (!empty($dr['is_grand_total']) && $dlScope !== 'Semua Leader') continue;
            if (empty($dr['is_grand_total']) && $dlScope !== 'Semua Leader' && $dr['leader'] !== $dlScope) continue;
            echo '<tr><td>' . htmlspecialchars($dr['leader']) . "</td><td>{$dr['so']}</td><td>{$dr['paid']}</td><td>{$dr['sa']}</td><td>{$dr['blm_so']}</td><td>{$dr['blm_paid']}</td><td>{$dr['blm_sa']}</td></tr>";
        }
        echo '</table><br><h3>2. DETAIL TARGET & KOMISI AGENT</h3><table border="1"><tr><th>SALES LEADER</th><th>SALES NAME</th><th>MASA KERJA</th><th>LEVEL</th><th>TARGET ALL</th>';
        if ($dlAdmin) echo '<th>Reguler</th><th>Yearly</th>';
        echo '<th>SA</th><th>PAID</th><th>GAP SA</th><th>PERSENTASE</th><th>STATUS MTD</th><th>Harus Paid/Hr</th><th>Harus SA/Hr</th><th>RUNRATE</th><th>3 Monthly</th><th>Monthly</th><th>Semesterly</th><th>Yearly</th><th>Estimasi Komisi</th></tr>';
        foreach ($dlAgents as $r) {
            echo '<tr><td>' . htmlspecialchars($r['leader']) . '</td><td>' . htmlspecialchars($r['name']) . '</td><td>' . htmlspecialchars($r['masa_kerja']) . '</td><td>' . htmlspecialchars($r['level']) . "</td><td>{$r['target_all']}</td>";
            if ($dlAdmin) echo "<td>{$r['target_reguler']}</td><td>{$r['target_yearly']}</td>";
            echo "<td>{$r['sa_nov']}</td><td>{$r['paid_nov']}</td><td>{$r['gap_sa']}</td><td>{$r['persen']}%</td><td>" . htmlspecialchars($r['status_mtd']) . "</td><td>{$r['harus_paid_hr']}</td><td>{$r['harus_sa_hr']}</td><td>{$r['runrate_30']}</td><td>{$r['p_3m']}</td><td>{$r['p_m']}</td><td>{$r['p_sem']}</td><td>{$r['p_yr']}</td><td>{$r['est_komisi']}</td></tr>";
        }
        echo '</table></body></html>';
        exit;
    }
}

// Handler Logout
if (isset($_GET['logout'])) {
    $_SESSION = [];
    if (ini_get("session.use_cookies")) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000, $params['path'], $params['domain'], $params['secure'], $params['httponly']);
    }
    session_destroy();
    header('Location: index.php');
    exit;
}

list($isLockedOut, $lockoutRemain) = rate_limit_status($rateLimitFile);
if ($isLockedOut && $_SERVER['REQUEST_METHOD'] !== 'POST') {
    $loginError = "🚫 FIREWALL LOCKOUT AKTIF: Terlalu banyak percobaan gagal. Form dikunci sementara selama {$lockoutRemain} detik, silakan muat ulang halaman setelah waktu habis.";
}

// ============================================================================
// HANDLER POST ACTIONS
// ============================================================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    $postedCsrf = $_POST['csrf_token'] ?? '';
    if (!hash_equals($csrfToken, $postedCsrf)) {
        $loginError = '🛡️ WAF Security: Token sesi CSRF tidak valid. Silakan muat ulang halaman.';
        $actionStatus = '<div class="alert-err">' . htmlspecialchars($loginError) . '</div>';
    } elseif ($_POST['action'] === 'login_cred') {
        if ($isLockedOut) {
            $loginError = "🚫 FIREWALL LOCKOUT AKTIF: Akses dikunci selama {$lockoutRemain} detik karena terlalu banyak percobaan login gagal.";
        } else {
            $rawU = trim((string)($_POST['username'] ?? ''));
            $rawP = trim((string)($_POST['password'] ?? ''));
            list($okU, $msgU) = waf_inspect_input($rawU, $auditLogFile);
            list($okP, $msgP) = waf_inspect_input($rawP, $auditLogFile);

            if (!$okU) {
                $loginError = $msgU;
            } elseif (!$okP) {
                $loginError = $msgP;
            } else {
                $found = authenticate_user($rawU, $rawP, $saCfg, $rolesCfg);
                if ($found) {
                    rate_limit_clear($rateLimitFile);
                    session_regenerate_id(true);
                    $_SESSION['auth_user'] = $found;
                    if (!empty($found['is_admin_master'])) {
                        // Disimpan hanya di memory session server untuk membuka Brankas Vault terenkripsi
                        $_SESSION['_sa_vault_key'] = $rawP;
                    } else {
                        unset($_SESSION['_sa_vault_key']);
                    }
                    waf_log_event($auditLogFile, 'AUTH-SUCCESS', $found['username'], 'Login berhasil sebagai ' . $found['role']);
                    header('Location: index.php');
                    exit;
                } else {
                    list($fails, $kenaLock) = rate_limit_fail($rateLimitFile, $auditLogFile, $rawU);
                    if ($kenaLock) {
                        $isLockedOut = true;
                        $lockoutRemain = 180;
                        $loginError = '🚫 FIREWALL LOCKOUT: Anda gagal login 5 kali berturut-turut. IP & sesi dikunci 3 menit!';
                    } else {
                        $sisaCoba = 5 - $fails;
                        if (is_blocked_legacy_cred(strtolower($rawU), $rawP)) {
                            $loginError = "⚠️ Kredensial lama telah dihapus demi keamanan. Gunakan ID & Password terbaru! (Sisa percobaan: {$sisaCoba}x)";
                        } else {
                            $loginError = "ID Pengguna atau Password tidak valid! (Sisa percobaan sebelum terkunci Firewall: {$sisaCoba}x).";
                        }
                    }
                }
            }
        }
    } elseif ($_POST['action'] === 'switch_daily_date' && !empty($_SESSION['auth_user'])) {
        // Ubah Tanggal Cek Rekap Harian & Agent Blm Produktif secara instan di server tanpa Docker / tanpa re-upload
        try {
            $hariCekIn = max(1, min(31, (int)($_POST['hari_harian_cek'] ?? 15)));
            if (!file_exists($targetActiveFile) && file_exists($targetDefaultFile)) {
                @copy($targetDefaultFile, $targetActiveFile);
            }
            $poolNow = load_prospect_pool($poolActiveFile, $poolDefaultFile);
            $pCur = $appData['params'] ?? ['sheet' => "NOVEMBER'26", 'bulan_lalu' => 10, 'bulan_ini' => 11, 'tahun' => 2026, 'total_hari' => 30, 'hari_berjalan' => 15, 'rasio_paid' => 1.25];
            $hDlmBln = cal_days_in_month_aman((int)$pCur['bulan_ini'], (int)$pCur['tahun']);
            $tglTargetObj = new DateTimeImmutable(sprintf('%04d-%02d-%02d', (int)$pCur['tahun'], (int)$pCur['bulan_ini'], min((int)$pCur['hari_berjalan'], $hDlmBln)));
            $targetRows = baca_data_target($targetActiveFile, (string)$pCur['sheet'], $tglTargetObj);
            $dp = hitung_rekap_harian_blm_produktif($poolNow, $targetRows, (int)$pCur['bulan_ini'], (int)$pCur['tahun'], $hariCekIn);
            $appData['daily_prod_date_label'] = $dp['date_label'];
            $appData['daily_prod_day'] = $dp['day'];
            $appData['daily_prod_rows'] = $dp['rows'];
            $appData['params']['hari_harian'] = $dp['day'];
            $appData['tanggal_tersedia'] = daftar_hari_tersedia_bulan($poolNow, (int)$pCur['bulan_ini'], (int)$pCur['tahun'], $dp['day']);
            file_put_contents($dataFile, json_encode($appData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
            $actionStatus = '<div class="alert-ok">📅 Tanggal Tabel Harian &amp; Agent Blm Produktif diubah ke <b>' . htmlspecialchars($dp['date_label']) . '</b> langsung di server!</div>';
        } catch (Throwable $e) {
            $actionStatus = '<div class="alert-err">❌ Gagal mengganti tanggal harian: ' . htmlspecialchars($e->getMessage()) . '</div>';
        }
    } elseif ($_POST['action'] === 'upload_excel_data' && !empty($_SESSION['auth_user'])) {
        $curRole = $_SESSION['auth_user']['role'] ?? '';
        if (!in_array($curRole, ['Admin', 'Leader'], true)) {
            $actionStatus = '<div class="alert-err">🚫 Akses Ditolak: Hanya Super Admin dan Sales Leader yang diizinkan mengupdate data di server!</div>';
        } else {
            try {
                $sheetInput   = trim((string)($_POST['sheet_name'] ?? "NOVEMBER'26"));
                $bulanLaluIn  = max(1, min(12, (int)($_POST['bulan_lalu'] ?? 10)));
                $bulanIniIn   = max(1, min(12, (int)($_POST['bulan_ini'] ?? 11)));
                $tahunIn      = max(2020, min(2035, (int)($_POST['tahun'] ?? 2026)));
                $totalHariIn  = max(1, min(31, (int)($_POST['total_hari'] ?? 30)));
                $hariJalanIn  = max(1, min($totalHariIn, (int)($_POST['hari_berjalan'] ?? 15)));
                $hariHarianIn = max(1, min(31, (int)($_POST['hari_harian'] ?? $hariJalanIn)));
                $rasioPaidIn  = max(0.5, min(5.0, (float)($_POST['rasio_paid'] ?? 1.25)));
                $modeProspect = ($_POST['mode_prospect'] ?? 'merge') === 'replace' ? 'replace' : 'merge';

                list($okSh, $msgSh) = waf_inspect_input($sheetInput, $auditLogFile);
                if (!$okSh) throw new RuntimeException($msgSh);

                $targetNama = $appData['sumber']['target'] ?? 'TARGET PER MONTH.xlsx';
                if (!empty($_FILES['file_target']['name']) && $_FILES['file_target']['error'] === UPLOAD_ERR_OK) {
                    $origTarget = basename((string)$_FILES['file_target']['name']);
                    if (strtolower(pathinfo($origTarget, PATHINFO_EXTENSION)) !== 'xlsx') {
                        throw new RuntimeException('File Target harus berformat .xlsx.');
                    }
                    if (!move_uploaded_file($_FILES['file_target']['tmp_name'], $targetActiveFile)) {
                        throw new RuntimeException('Gagal menyimpan file Target ke folder server.');
                    }
                    $targetNama = $origTarget;
                }
                if (!file_exists($targetActiveFile) && file_exists($targetDefaultFile)) {
                    @copy($targetDefaultFile, $targetActiveFile);
                }
                if (!file_exists($targetActiveFile)) {
                    throw new RuntimeException('File Target (.xlsx) belum tersedia di server.');
                }

                $uploadedProspects = [];
                $tmpFilesToClean = [];
                if (!empty($_FILES['file_prospect']['name'])) {
                    $names = (array)$_FILES['file_prospect']['name'];
                    $tmps  = (array)$_FILES['file_prospect']['tmp_name'];
                    $errs  = (array)$_FILES['file_prospect']['error'];
                    for ($i = 0; $i < count($names); $i++) {
                        if (empty($names[$i]) || $errs[$i] !== UPLOAD_ERR_OK) continue;
                        $origP = basename((string)$names[$i]);
                        $extP = strtolower(pathinfo($origP, PATHINFO_EXTENSION));
                        if (!in_array($extP, ['xls', 'xlsx', 'csv', 'tsv', 'html', 'htm'], true)) {
                            throw new RuntimeException("Format file prospect '$origP' tidak didukung. Gunakan .xls, .xlsx, atau .csv.");
                        }
                        $destP = $uploadsDir . '/tmp_prospect_' . time() . '_' . $i . '.' . $extP;
                        if (move_uploaded_file($tmps[$i], $destP)) {
                            $uploadedProspects[] = ['path' => $destP, 'name' => $origP];
                            $tmpFilesToClean[] = $destP;
                        }
                    }
                }

                $existingPool = ($modeProspect === 'merge' || empty($uploadedProspects))
                    ? load_prospect_pool($poolActiveFile, $poolDefaultFile)
                    : [];

                if (empty($existingPool) && empty($uploadedProspects)) {
                    throw new RuntimeException('Pilih minimal 1 file list_prospect (.xls / .xlsx / .csv) untuk diupload.');
                }

                $hasilBaru = proses_data([
                    'target_path'        => $targetActiveFile,
                    'target_name'        => $targetNama,
                    'sheet'              => $sheetInput,
                    'prospect_rows_awal' => $existingPool,
                    'prospects'          => $uploadedProspects,
                    'bulan_lalu'         => $bulanLaluIn,
                    'bulan_ini'          => $bulanIniIn,
                    'tahun'              => $tahunIn,
                    'total_hari'         => $totalHariIn,
                    'hari_berjalan'      => $hariJalanIn,
                    'hari_harian'        => $hariHarianIn,
                    'rasio_paid'         => $rasioPaidIn,
                    'simpan_pool_path'   => $poolActiveFile,
                ]);
                foreach ($tmpFilesToClean as $tf) @unlink($tf);

                $hasilBaru['bot_token_default'] = $appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs';
                $hasilBaru['docker_tunnel_url'] = $appData['docker_tunnel_url'] ?? '';
                $hasilBaru['sumber']['updated_at'] = date('Y-m-d H:i:s');
                $hasilBaru['sumber']['updated_by'] = $_SESSION['auth_user']['display_name'] . ' (' . $curRole . ')';

                file_put_contents($dataFile, json_encode($hasilBaru, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
                $appData = $hasilBaru;
                waf_log_event($auditLogFile, 'DATA-UPDATE', $_SESSION['auth_user']['username'] ?? $curRole, 'Update server selesai: ' . ($hasilBaru['periode_label'] ?? ''));

                $jmlAgen = count($hasilBaru['agent_rows'] ?? []);
                $jmlBarisP = number_format((int)($hasilBaru['sumber']['total_baris_prospect'] ?? 0), 0, ',', '.');
                $infoUploadStr = !empty($uploadedProspects)
                    ? ('File Baru: ' . implode(', ', array_column($uploadedProspects, 'name')))
                    : 'Database Prospect Aktif Server';

                $actionStatus = '<div class="alert-ok">✅ <b>SEMUA DATA BERHASIL DI-UPDATE LANGSUNG KE SERVER (TANPA DOCKER)!</b><br>'
                    . '📊 Sheet Target: <b>' . htmlspecialchars($sheetInput) . '</b> (' . $jmlAgen . ' Agen) | '
                    . '📂 Total Prospect Unik: <b>' . $jmlBarisP . ' baris</b> (' . htmlspecialchars($infoUploadStr) . ') | '
                    . '🗓 Periode MTD: <b>' . htmlspecialchars($hasilBaru['periode_label']) . ' (' . $hasilBaru['target_persen_mtd'] . '%)</b> | '
                    . '📅 Cek Harian: <b>' . htmlspecialchars($hasilBaru['daily_prod_date_label'] ?? '') . '</b></div>';
            } catch (Throwable $e) {
                $actionStatus = '<div class="alert-err">❌ <b>Gagal Memproses Data Excel:</b> ' . htmlspecialchars($e->getMessage()) . '</div>';
            }
        }
    } elseif ($_POST['action'] === 'reset_default_data' && !empty($_SESSION['auth_user'])) {
        $curRole = $_SESSION['auth_user']['role'] ?? '';
        if (!in_array($curRole, ['Admin', 'Leader'], true)) {
            $actionStatus = '<div class="alert-err">🚫 Akses Ditolak!</div>';
        } else {
            if (file_exists($defaultDataFile)) @copy($defaultDataFile, $dataFile);
            if (file_exists($targetDefaultFile)) @copy($targetDefaultFile, $targetActiveFile);
            if (file_exists($poolDefaultFile)) @copy($poolDefaultFile, $poolActiveFile);
            $appData = load_json_safe($dataFile, []);
            waf_log_event($auditLogFile, 'DATA-RESET', $_SESSION['auth_user']['username'] ?? $curRole, 'Reset ke dataset default server');
            $actionStatus = '<div class="alert-ok">♻️ <b>Data Dashboard Server dikembalikan ke Dataset Default!</b></div>';
        }
    } elseif ($_POST['action'] === 'update_all_credentials' && !empty($_SESSION['auth_user']['is_admin_master'])) {
        try {
            $saKeyNow = (string)($_SESSION['_sa_vault_key'] ?? '');
            $curVault = ($saKeyNow !== '' && !empty($rolesCfg['vault_enc']) && !empty($rolesCfg['vault_salt']))
                ? (vault_decrypt_php((string)$rolesCfg['vault_enc'], $saKeyNow, (string)$rolesCfg['vault_salt']) ?? [])
                : [];

            $targetRole = $_POST['target_role'] ?? 'superadmin';
            if ($targetRole === 'superadmin') {
                $newSaUser = strtolower(trim((string)($_POST['new_sa_user'] ?? '')));
                $newSaPass = trim((string)($_POST['new_sa_pass'] ?? ''));
                if (!preg_match('/^[a-z0-9._\-]{6,40}$/', $newSaUser) || is_blocked_legacy_cred($newSaUser, $newSaPass)) {
                    throw new RuntimeException('ID Super Admin baru harus 6-40 karakter & tidak boleh memakai ID lama/umum.');
                }
                if (strlen($newSaPass) < 10) {
                    throw new RuntimeException('Password Super Admin baru minimal 10 karakter!');
                }
                $newSalt = bin2hex(random_bytes(16));
                $newIter = 200000;
                $newHash = hash_pbkdf2('sha256', $newSaPass, $newSalt, $newIter, 64, false);
                $saCfg = ['username' => $newSaUser, 'salt' => $newSalt, 'iterations' => $newIter, 'hash' => $newHash, 'updated_at' => date('Y-m-d H:i:s')];
                file_put_contents($superAdminStoreFile, json_encode($saCfg, JSON_PRETTY_PRINT), LOCK_EX);
                $_SESSION['auth_user']['username'] = $newSaUser;
                $_SESSION['_sa_vault_key'] = $newSaPass;
                $saKeyNow = $newSaPass;
                if (!empty($curVault)) {
                    $curVault['super_admin_id'] = $newSaUser;
                    $curVault['updated_at'] = date('Y-m-d H:i:s');
                }
                $msgOk = "🔐 Kredensial <b>Super Admin</b> berhasil diperbarui di server: ID <code>" . htmlspecialchars($newSaUser) . "</code>!";
            } elseif ($targetRole === 'finance') {
                $finU = strtolower(trim((string)($_POST['new_fin_user'] ?? '')));
                $finP = trim((string)($_POST['new_fin_pass'] ?? ''));
                if (!preg_match('/^[a-z0-9._\-]{5,40}$/', $finU) || is_blocked_legacy_cred($finU, $finP) || strlen($finP) < 8) {
                    throw new RuntimeException('ID Finance minimal 5 karakter (bukan ID lama) & Password minimal 8 karakter.');
                }
                $rolesCfg['finance'] = ['username' => $finU, 'hash' => hash('sha256', $finP)];
                if (!empty($curVault)) $curVault['finance'] = ['id' => $finU, 'pass' => $finP];
                $msgOk = "💳 ID/Password <b>Finance</b> diperbarui di server: <code>" . htmlspecialchars($finU) . "</code>";
            } elseif ($targetRole === 'leader_pass') {
                $ldrP = trim((string)($_POST['new_ldr_pass'] ?? ''));
                if (strlen($ldrP) < 8 || is_blocked_legacy_cred('x', $ldrP)) {
                    throw new RuntimeException('Password Leader baru minimal 8 karakter & bukan password lama.');
                }
                $hLdr = hash('sha256', $ldrP);
                $rolesCfg['leader_default_hash'] = $hLdr;
                foreach (($rolesCfg['leaders'] ?? []) as $lk => $lv) {
                    $rolesCfg['leaders'][$lk]['hash'] = $hLdr;
                }
                if (!empty($curVault)) $curVault['leaders']['pass_default'] = $ldrP;
                $msgOk = "👨‍💼 Password seluruh <b>Sales Leader</b> berhasil diperbarui di server!";
            } elseif ($targetRole === 'agen_pass') {
                $agtP = trim((string)($_POST['new_agt_pass'] ?? ''));
                if (strlen($agtP) < 8 || is_blocked_legacy_cred('x', $agtP)) {
                    throw new RuntimeException('Password Agen baru minimal 8 karakter & bukan password lama.');
                }
                $hAgt = hash('sha256', $agtP);
                $rolesCfg['agen_default_hash'] = $hAgt;
                foreach (($rolesCfg['agen_accounts'] ?? []) as $ak => $av) {
                    $rolesCfg['agen_accounts'][$ak]['hash'] = $hAgt;
                }
                if (!empty($curVault)) $curVault['agen']['pass_default'] = $agtP;
                $msgOk = "👤 Password seluruh <b>Agen Telesales</b> berhasil diperbarui di server!";
            } else {
                throw new RuntimeException('Role target tidak valid.');
            }

            if ($saKeyNow !== '' && !empty($curVault)) {
                $vSalt = bin2hex(random_bytes(16));
                $rolesCfg['vault_salt'] = $vSalt;
                $rolesCfg['vault_enc']  = vault_encrypt_php($curVault, $saKeyNow, $vSalt);
            }
            file_put_contents($rolesStoreFile, json_encode($rolesCfg, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE), LOCK_EX);
            waf_log_event($auditLogFile, 'CRED-UPDATE', $_SESSION['auth_user']['username'] ?? 'sa', "Update role: {$targetRole}");
            $actionStatus = '<div class="alert-ok">' . $msgOk . '</div>';
        } catch (Throwable $e) {
            $actionStatus = '<div class="alert-err">❌ ' . htmlspecialchars($e->getMessage()) . '</div>';
        }
    } elseif ($_POST['action'] === 'send_telegram' && !empty($_SESSION['auth_user'])) {
        $defaultToken = $appData['bot_token_default'] ?? '';
        $botToken = trim((string)($_POST['bot_token'] ?? $defaultToken));
        $chatId = trim((string)($_POST['chat_id'] ?? ''));
        $scopeSend = $_POST['scope_send'] ?? 'Yovi Arian';
        $agentRowsTg = $appData['agent_rows'] ?? [];
        $dailyRowsTg = $appData['daily_prod_rows'] ?? [];
        $dailyLblTg  = $appData['daily_prod_date_label'] ?? '';
        $targetMtdTg = $appData['target_persen_mtd'] ?? 50;
        $periodeLabelTg = $appData['periode_label'] ?? '';
        $sisaHariTg = $appData['sisa_hari'] ?? 15;

        list($okChat, $msgChat) = waf_inspect_input($chatId, $auditLogFile);
        if (!$okChat) {
            $tgStatus = '<div class="alert-err">' . htmlspecialchars($msgChat) . '</div>';
        } elseif (!$chatId) {
            $tgStatus = '<div class="alert-err">❌ Masukkan TELEGRAM_CHAT_ID terlebih dahulu (ketik /id di Bot Telegram untuk melihat Chat ID).</div>';
        } else {
            $blocks = [];
            $hdrTg = "📊 <b>LAPORAN PERFORMA &amp; TARGET TELESALES ISP</b>\n"
                . "🌐 Portal Resmi : <b>https://laporantelesalesoxygen.my.id</b>\n"
                . "👨‍💼 Scope Leader : <b>" . htmlspecialchars($scopeSend) . "</b>\n"
                . "🗓 Periode : <b>$periodeLabelTg | Target MTD: {$targetMtdTg}%</b> (Sisa $sisaHariTg Hari)\n"
                . "━━━━━━━━━━━━━━━━━━━━━━\n";

            // Ringkasan Rekap Harian & Agent Belum Produktif
            if (!empty($dailyRowsTg)) {
                $dpLines = ["📅 <b>REKAP HARIAN ({$dailyLblTg}) &amp; AGENT BLM PRODUKTIF</b>"];
                foreach ($dailyRowsTg as $dr) {
                    $isGt = !empty($dr['is_grand_total']);
                    if (!$isGt && $scopeSend !== 'Semua Leader' && $dr['leader'] !== $scopeSend) continue;
                    $dpLines[] = ($isGt ? "🏆 <b>" : "• <b>") . htmlspecialchars($dr['leader']) . "</b>: SO=<b>{$dr['so']}</b> PAID=<b>{$dr['paid']}</b> SA=<b>{$dr['sa']}</b> | Blm Prod: SO=<b>{$dr['blm_so']}</b> PAID=<b>{$dr['blm_paid']}</b> SA=<b>{$dr['blm_sa']}</b>";
                }
                $blocks[] = implode("\n", $dpLines) . "\n━━━━━━━━━━━━━━━━━━━━━━\n";
            }

            $no = 1;
            $totT = 0; $totSa = 0; $totPaid = 0; $totKom = 0;
            foreach ($agentRowsTg as $ag) {
                if ($scopeSend !== 'Semua Leader' && $ag['leader'] !== $scopeSend) continue;
                if (strtoupper($ag['name']) === 'VACANT') continue;
                $totT += $ag['target_all'];
                $totSa += $ag['sa_nov'];
                $totPaid += $ag['paid_nov'];
                $totKom += $ag['est_komisi'];
                $komStr = 'Rp ' . number_format($ag['est_komisi'], 0, ',', '.');
                $blocks[] = "<b>{$no}. 👤 " . htmlspecialchars($ag['name']) . "</b> ({$ag['level']})\n"
                    . "├ 📌 Status MTD : <b>{$ag['status_mtd']}</b> ({$ag['persen']}%)\n"
                    . "├ ✅ Realisasi : <b>{$ag['sa_nov']} SA</b> | <b>{$ag['paid_nov']} Paid</b> | Gap: {$ag['gap_sa']}\n"
                    . "├ ⚡ Wajib Harian : <b>{$ag['harus_paid_hr']} Paid/hr</b> &amp; <b>{$ag['harus_sa_hr']} SA/hr</b>\n"
                    . "└ 🎯 Target Total : <b>{$ag['target_all']} SA</b> | 💰 <b>$komStr</b>\n";
                $no++;
            }
            $pctTim = $totT > 0 ? round(($totSa / $totT) * 100) : 0;
            $totKomStr = 'Rp ' . number_format($totKom, 0, ',', '.');
            $blocks[] = "━━━━━━━━━━━━━━━━━━━━━━\n🏆 <b>TOTAL TIM: {$totSa} SA / Target {$totT} SA ({$pctTim}%) | {$totKomStr}</b>";

            // Pecah otomatis per <= 3600 karakter agar SEMUA agen terkirim utuh tanpa terpotong
            $messages = [];
            $curMsg = $hdrTg;
            foreach ($blocks as $b) {
                $add = $b . "\n";
                if (strlen($curMsg) + strlen($add) > 3600) {
                    $messages[] = trim($curMsg);
                    $curMsg = "📋 <b>Lanjutan Laporan (" . htmlspecialchars($scopeSend) . ")</b>\n━━━━━━━━━━━━━━━━━━━━━━\n" . $add;
                } else {
                    $curMsg .= $add;
                }
            }
            if (trim($curMsg) !== '') $messages[] = trim($curMsg);

            $okAll = true;
            $errMsg = '';
            $urlTg = "https://api.telegram.org/bot{$botToken}/sendMessage";
            foreach ($messages as $mTxt) {
                $ch = curl_init($urlTg);
                curl_setopt($ch, CURLOPT_POST, true);
                curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query(['chat_id' => $chatId, 'text' => $mTxt, 'parse_mode' => 'HTML']));
                curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
                curl_setopt($ch, CURLOPT_TIMEOUT, 15);
                $resp = curl_exec($ch);
                $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
                curl_close($ch);
                if ($httpCode !== 200) {
                    $okAll = false;
                    $errMsg = "HTTP {$httpCode}: " . (string)$resp;
                    break;
                }
            }

            if ($okAll) {
                $tgStatus = '<div class="alert-ok">✅ Laporan lengkap berhasil dikirim ke Telegram Chat ID <b>' . htmlspecialchars($chatId) . '</b> (' . count($messages) . ' pesan, HTTP 200 OK)!</div>';
            } else {
                $tgStatus = '<div class="alert-err">❌ Gagal mengirim ke Telegram (' . htmlspecialchars($errMsg) . ')</div>';
            }
        }
    }
}

// Variabel tampilan terbaru dari $appData
$mtdRows      = $appData['mtd_rows'] ?? [];
$agentRows    = $appData['agent_rows'] ?? [];
$dailyRows    = $appData['daily_prod_rows'] ?? [];
$dailyLbl     = (string)($appData['daily_prod_date_label'] ?? '15-Nov-26');
$dailyDay     = (int)($appData['daily_prod_day'] ?? 15);
$tglTersedia  = $appData['tanggal_tersedia'] ?? [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15];
$targetMtd    = (int)($appData['target_persen_mtd'] ?? 50);
$periodeLabel = $appData['periode_label'] ?? '15-Nov-2026';
$hariBerjalan = (int)($appData['hari_berjalan'] ?? 15);
$totalHari    = (int)($appData['total_hari'] ?? 30);
$sisaHari     = (int)($appData['sisa_hari'] ?? 15);
$kolOct       = $appData['kol_oct'] ?? ('SA OCT 1-' . $hariBerjalan);
$kolNov       = $appData['kol_nov'] ?? ('SA NOV 1-' . $hariBerjalan);
$lblBlnIni    = $appData['label_bulan_ini'] ?? 'NOV';
$defaultToken = $appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs';
$paramsCur    = $appData['params'] ?? [
    'sheet' => "NOVEMBER'26",
    'bulan_lalu' => 10,
    'bulan_ini' => 11,
    'tahun' => 2026,
    'total_hari' => 30,
    'hari_berjalan' => 15,
    'hari_harian' => 15,
    'rasio_paid' => 1.25,
];
$sumberCur    = $appData['sumber'] ?? [];

$leaders = [];
foreach ($agentRows as $r) {
    if (!in_array($r['leader'], $leaders, true)) {
        $leaders[] = $r['leader'];
    }
}
sort($leaders);

$authUser = $_SESSION['auth_user'] ?? null;
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
        .container { max-width: 1460px; margin: 0 auto; padding: 18px 22px; }
        .hero {
            background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #1d4ed8 100%);
            color: #fff; padding: 24px 28px; border-radius: 16px;
            box-shadow: 0 10px 25px rgba(15,23,42,0.22); margin-bottom: 18px;
            display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 14px;
        }
        .hero h1 { margin: 0 0 6px 0; font-size: 1.52rem; font-weight: 800; }
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
        .grid-2 { display: grid; grid-template-columns: repeat(auto-fit, minmax(310px, 1fr)); gap: 16px; }
        .grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
        .grid-4 { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); gap: 14px; margin-bottom: 18px; }
        .metric-box {
            background: #fff; border: 1px solid #e2e8f0; border-left: 5px solid #2563eb;
            border-radius: 12px; padding: 14px 18px; box-shadow: 0 2px 8px rgba(15,23,42,0.04);
        }
        .metric-label { font-size: 0.78rem; color: #64748b; font-weight: 700; text-transform: uppercase; }
        .metric-val { font-size: 1.45rem; font-weight: 800; color: #0f172a; margin-top: 4px; }
        .metric-sub { font-size: 0.8rem; color: #16a34a; font-weight: 600; margin-top: 2px; }
        input, select {
            width: 100%; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px;
            font-size: 0.9rem; margin-top: 4px; margin-bottom: 10px; background: #fff;
        }
        input[type="file"] { padding: 8px; background: #f8fafc; border: 2px dashed #94a3b8; cursor: pointer; }
        .btn {
            display: inline-block; background: #2563eb; color: #fff; border: none;
            padding: 11px 18px; border-radius: 8px; font-weight: 700; cursor: pointer;
            text-decoration: none; font-size: 0.9rem; text-align: center;
        }
        .btn:hover { background: #1d4ed8; }
        .btn-green { background: #059669; }
        .btn-green:hover { background: #047857; }
        .btn-amber { background: #d97706; }
        .btn-amber:hover { background: #b45309; }
        .btn-red { background: #dc2626; }
        .btn-red:hover { background: #b91c1c; }
        .table-wrap { overflow-x: auto; }
        table { width: 100%; border-collapse: collapse; font-size: 0.84rem; }
        th {
            background: #14365d; color: #fff; padding: 9px 10px; text-align: center;
            border: 1px solid #cbd5e1; white-space: nowrap;
        }
        th.navy-hdr { background: #002060 !important; border-color: #334155 !important; }
        th.red-hdr { background: #dc0000 !important; border-color: #991b1b !important; }
        td { padding: 7px 10px; border: 1px solid #cbd5e1; text-align: center; white-space: nowrap; }
        td.left { text-align: left; }
        tr.row-total td { background: #8ea9db !important; font-weight: 800; color: #0f172a; }
        tr.row-subtotal td { background: #b4a7d6 !important; font-weight: 800; color: #0f172a; }
        tr.row-vacant td { background: #ffff00 !important; font-weight: 700; }
        tr.row-grand td { background: #ffffff; font-weight: 800; color: #0f172a; border-top: 2px solid #0f172a; }
        td.peach-cell { background: #fce4d6 !important; font-weight: 800; color: #9a3412; }
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
        .alert-err { background: #fee2e2; color: #991b1b; padding: 13px 16px; border-radius: 10px; margin-bottom: 16px; font-weight: 600; border: 1px solid #fca5a5; }
        .alert-ok { background: #dcfce7; color: #166534; padding: 13px 16px; border-radius: 10px; margin-bottom: 16px; font-weight: 600; border: 1px solid #86efac; }
        .spotlight {
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            color: #fff; padding: 18px 22px; border-radius: 14px; border-left: 6px solid #10b981; margin-bottom: 18px;
        }
        details.vault-box {
            background: #0f172a; color: #f8fafc; padding: 14px 18px; border-radius: 12px;
            margin-bottom: 18px; border: 1px solid #334155;
        }
        details.vault-box summary { cursor: pointer; font-weight: 800; font-size: 0.96rem; color: #fde047; }
        .upload-panel {
            background: linear-gradient(135deg, #f8fafc 0%, #eff6ff 100%);
            border: 2px solid #93c5fd; border-radius: 14px; padding: 18px 22px; margin-bottom: 20px;
        }
        pre.log-box {
            background: #020617; color: #86efac; padding: 12px; border-radius: 8px;
            font-size: 0.78rem; overflow-x: auto; max-height: 220px;
        }
    </style>
</head>
<body>
<div class="container">
<?php if (!$authUser): ?>
    <div class="login-wrap">
        <div class="hero" style="text-align:center; display:block;">
            <div style="font-size:2.4rem;">🛡️🔒</div>
            <h1>Portal Eksekutif Telesales ISP</h1>
            <p>Sistem Mandiri Sisi Server (Non-Docker) — Terproteksi WAF, IP Rate-Limiter &amp; PBKDF2-SHA256</p>
            <div class="badge-bar" style="justify-content:center; margin-top:12px;">
                <span class="badge">🛡️ WAF Firewall: ACTIVE</span>
                <span class="badge">🔐 PBKDF2-SHA256 Auth</span>
                <span class="badge">🚫 Anti-Brute Force IP</span>
            </div>
        </div>

        <?php if ($loginError): ?>
            <div class="alert-err">❌ <?= htmlspecialchars($loginError) ?></div>
        <?php endif; ?>

        <div class="card">
            <h3 style="margin-top:0;">🔐 Autentikasi Pengguna Resmi</h3>
            <p style="font-size:0.84rem; color:#64748b; margin-top:0;">
                Masukkan ID Pengguna dan Password resmi terbaru Anda. Seluruh kredensial disembunyikan dan hanya dikelola oleh <b>Super Admin</b>.
            </p>
            <form method="post" autocomplete="off">
                <input type="hidden" name="action" value="login_cred">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                <label><b>ID Pengguna / Username</b></label>
                <input type="text" name="username" placeholder="Masukkan ID Pengguna resmi..." required <?= $isLockedOut ? 'disabled' : '' ?>>
                <label><b>Password</b></label>
                <input type="password" name="password" placeholder="Masukkan Password resmi..." required <?= $isLockedOut ? 'disabled' : '' ?>>
                <button type="submit" class="btn" style="width:100%; margin-top:6px;" <?= $isLockedOut ? 'disabled' : '' ?>>🚀 Masuk dengan Aman (WAF Verified)</button>
            </form>
        </div>
    </div>
<?php else:
    $role = $authUser['role'];
    $isAdminMaster = !empty($authUser['is_admin_master']);
    $isAdmin = in_array($role, ['Admin', 'Finance'], true);
    $canUploadExcel = in_array($role, ['Admin', 'Leader'], true);
    $selectedScope = $_GET['scope'] ?? $authUser['leader_scope'];
    if ($role === 'Leader' || $role === 'Agen') {
        $selectedScope = $authUser['leader_scope'];
    }

    $filteredAgents = array_values(array_filter($agentRows, fn($r) => $selectedScope === 'Semua Leader' || $r['leader'] === $selectedScope));

    $sumTargetAll = 0; $sumSaNov = 0; $sumPaidNov = 0; $sumKomisi = 0; $sumRevNetto = 0; $kurangCount = 0;
    foreach ($filteredAgents as $r) {
        $sumTargetAll += $r['target_all'];
        $sumSaNov += $r['sa_nov'];
        $sumPaidNov += $r['paid_nov'];
        $sumKomisi += $r['est_komisi'];
        $sumRevNetto += $r['rev_netto'];
        if (strtoupper($r['name']) !== 'VACANT' && $r['persen'] < $targetMtd) {
            $kurangCount++;
        }
    }
    $overallPct = $sumTargetAll > 0 ? round(($sumSaNov / $sumTargetAll) * 100) : 0;

    // Dekripsi Brankas Vault hanya jika Super Admin aktif dan punya Master Session Key
    $unlockedVault = null;
    if ($isAdminMaster && !empty($_SESSION['_sa_vault_key']) && !empty($rolesCfg['vault_enc']) && !empty($rolesCfg['vault_salt'])) {
        $unlockedVault = vault_decrypt_php((string)$rolesCfg['vault_enc'], (string)$_SESSION['_sa_vault_key'], (string)$rolesCfg['vault_salt']);
    }
?>
    <div class="hero">
        <div>
            <h1>📊 Dashboard Telesales Oxygen ISP — laporantelesalesoxygen.my.id</h1>
            <p>100% Real-Time Sisi Server (Non-Docker): MTD SA, Rekap Harian Blm Produktif, Detail Komisi, Upload Excel &amp; Telegram</p>
            <div class="badge-bar">
                <span class="badge">👤 Login: <?= htmlspecialchars($authUser['display_name']) ?> (<?= htmlspecialchars($role) ?>)</span>
                <span class="badge">👨‍💼 Scope: <?= htmlspecialchars($selectedScope) ?></span>
                <span class="badge">🗓 Periode: <?= htmlspecialchars($periodeLabel) ?> (MTD <?= $targetMtd ?>%)</span>
                <span class="badge">🛡️ WAF &amp; Rate-Limiter: ACTIVE</span>
            </div>
        </div>
        <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
            <?php if ($isAdmin): ?>
                <form method="get" style="margin:0; display:flex; gap:6px; align-items:center;">
                    <select name="scope" onchange="this.form.submit()" style="margin:0; width:215px;">
                        <option value="Semua Leader" <?= $selectedScope === 'Semua Leader' ? 'selected' : '' ?>>🌎 Semua Sales Leader</option>
                        <?php foreach ($leaders as $ldr): ?>
                            <option value="<?= htmlspecialchars($ldr) ?>" <?= $selectedScope === $ldr ? 'selected' : '' ?>>👨‍💼 <?= htmlspecialchars($ldr) ?></option>
                        <?php endforeach; ?>
                    </select>
                </form>
            <?php endif; ?>
            <a href="?download=excel&amp;scope=<?= urlencode($selectedScope) ?>" class="btn btn-green">📥 Download Excel (.xls)</a>
            <a href="?download=csv&amp;scope=<?= urlencode($selectedScope) ?>" class="btn">📄 CSV</a>
            <a href="?logout=1" class="btn btn-red">🚪 Logout</a>
        </div>
    </div>

    <?= $actionStatus ?>
    <?= $tgStatus ?>

    <?php if ($isAdminMaster): ?>
        <!-- BRANKAS & PENGELOLA ID/PASSWORD SEMUA ROLE (KHUSUS SUPER ADMIN) -->
        <details class="vault-box">
            <summary>🔐 BRANKAS &amp; PENGELOLA ID/PASSWORD SELURUH ROLE + LOG WAF (KHUSUS SUPER ADMIN)</summary>
            <div style="margin-top:14px; background:#fff; color:#0f172a; padding:16px; border-radius:10px;">
                <p style="margin:0 0 10px 0; font-size:0.84rem; color:#0f172a;">
                    ✅ Seluruh ID &amp; password lama (<code>admin/admin123</code>, <code>finance/finance123</code>, <code>leader123</code>, <code>agen123</code>) <b>diblokir permanen</b>.
                </p>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr><th>Role</th><th>ID Pengguna Resmi</th><th>Password Aktif</th><th>Hak Akses</th></tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td><b>👑 Super Admin</b></td>
                                <td><code><?= htmlspecialchars($saCfg['username']) ?></code></td>
                                <td><code><?= htmlspecialchars((string)($_SESSION['_sa_vault_key'] ?? '🔒 Terenkripsi PBKDF2')) ?></code></td>
                                <td class="left">Akses Penuh + Upload Excel + Kelola Semua ID/Pass + Audit WAF</td>
                            </tr>
                            <tr>
                                <td><b>💳 Finance</b></td>
                                <td><code><?= htmlspecialchars((string)($rolesCfg['finance']['username'] ?? ($unlockedVault['finance']['id'] ?? '-'))) ?></code></td>
                                <td><code><?= htmlspecialchars((string)($unlockedVault['finance']['pass'] ?? '🔒 Terenkripsi')) ?></code></td>
                                <td class="left">Semua Leader | Revenue Netto (PPN 11%) &amp; Estimasi Komisi</td>
                            </tr>
                            <tr>
                                <td><b>👨‍💼 Sales Leader (11 Tim)</b></td>
                                <td class="left"><code><?= htmlspecialchars(implode(', ', array_keys($rolesCfg['leaders'] ?? []))) ?></code></td>
                                <td><code><?= htmlspecialchars((string)($unlockedVault['leaders']['pass_default'] ?? '🔒 Terenkripsi')) ?></code></td>
                                <td class="left">Upload Excel + Monitoring Tim Sendiri + Rekap Blm Produktif + Telegram</td>
                            </tr>
                            <tr>
                                <td><b>👤 Agen Telesales (<?= count($rolesCfg['agen_accounts'] ?? []) ?> Akun)</b></td>
                                <td class="left">Format unik <code>agt_&lt;nama&gt;</code> (lihat daftar lengkap di bawah)</td>
                                <td><code><?= htmlspecialchars((string)($unlockedVault['agen']['pass_default'] ?? '🔒 Terenkripsi')) ?></code></td>
                                <td class="left">Kartu Performa Pribadi &amp; Kuota Harian Tim</td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <?php if (!empty($rolesCfg['agen_accounts'])): ?>
                    <details style="margin-top:12px; background:#f8fafc; padding:10px 14px; border-radius:8px; border:1px solid #cbd5e1;">
                        <summary style="cursor:pointer; font-weight:700; color:#1e3a8a;">📋 Daftar Lengkap <?= count($rolesCfg['agen_accounts']) ?> ID Unik Agen Telesales (Tanpa Bentrok)</summary>
                        <div class="table-wrap" style="max-height:260px; overflow-y:auto; margin-top:8px;">
                            <table>
                                <thead><tr><th>No</th><th>ID Login Agen</th><th>Nama Agen</th><th>Sales Leader</th></tr></thead>
                                <tbody>
                                <?php $idxA = 1; foreach ($rolesCfg['agen_accounts'] as $uidA => $metaA): ?>
                                    <tr>
                                        <td><?= $idxA++ ?></td>
                                        <td><code><?= htmlspecialchars($uidA) ?></code></td>
                                        <td class="left"><?= htmlspecialchars((string)$metaA['name']) ?></td>
                                        <td class="left"><?= htmlspecialchars((string)$metaA['leader']) ?></td>
                                    </tr>
                                <?php endforeach; ?>
                                </tbody>
                            </table>
                        </div>
                    </details>
                <?php endif; ?>

                <hr style="margin:16px 0; border:0; border-top:1px solid #e2e8f0;">
                <h4 style="margin:0 0 10px 0;">🔑 Ubah ID &amp; Password Semua Role Langsung di Server</h4>
                <div class="grid-2">
                    <form method="post" style="background:#f8fafc; padding:12px; border-radius:8px; border:1px solid #cbd5e1;">
                        <input type="hidden" name="action" value="update_all_credentials">
                        <input type="hidden" name="target_role" value="superadmin">
                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                        <b>👑 Ganti Super Admin:</b>
                        <input type="text" name="new_sa_user" value="<?= htmlspecialchars($saCfg['username']) ?>" placeholder="ID Super Admin baru..." required>
                        <input type="password" name="new_sa_pass" placeholder="Password Super Admin baru (min 10 char)..." required>
                        <button type="submit" class="btn btn-amber" style="width:100%;">Simpan Super Admin</button>
                    </form>

                    <form method="post" style="background:#f8fafc; padding:12px; border-radius:8px; border:1px solid #cbd5e1;">
                        <input type="hidden" name="action" value="update_all_credentials">
                        <input type="hidden" name="target_role" value="finance">
                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                        <b>💳 Ganti Akun Finance:</b>
                        <input type="text" name="new_fin_user" value="<?= htmlspecialchars((string)($rolesCfg['finance']['username'] ?? 'fin_oxygen26')) ?>" required>
                        <input type="password" name="new_fin_pass" placeholder="Password Finance baru (min 8 char)..." required>
                        <button type="submit" class="btn" style="width:100%;">Simpan Finance</button>
                    </form>

                    <form method="post" style="background:#f8fafc; padding:12px; border-radius:8px; border:1px solid #cbd5e1;">
                        <input type="hidden" name="action" value="update_all_credentials">
                        <input type="hidden" name="target_role" value="leader_pass">
                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                        <b>👨‍💼 Ganti Password Semua Sales Leader:</b>
                        <input type="password" name="new_ldr_pass" placeholder="Password Sales Leader baru (min 8 char)..." required>
                        <button type="submit" class="btn" style="width:100%;">Simpan Password Leader</button>
                    </form>

                    <form method="post" style="background:#f8fafc; padding:12px; border-radius:8px; border:1px solid #cbd5e1;">
                        <input type="hidden" name="action" value="update_all_credentials">
                        <input type="hidden" name="target_role" value="agen_pass">
                        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                        <b>👤 Ganti Password Semua Agen Telesales:</b>
                        <input type="password" name="new_agt_pass" placeholder="Password Agen baru (min 8 char)..." required>
                        <button type="submit" class="btn" style="width:100%;">Simpan Password Agen</button>
                    </form>
                </div>

                <hr style="margin:16px 0; border:0; border-top:1px solid #e2e8f0;">
                <b>🛡️ Monitor Log WAF &amp; Audit Keamanan Server (20 Terbaru):</b>
                <pre class="log-box"><?= htmlspecialchars(implode("\n", waf_read_logs($auditLogFile, 20))) ?></pre>
            </div>
        </details>
    <?php endif; ?>

    <?php if ($canUploadExcel): ?>
        <!-- PANEL UPLOAD & UPDATE EXCEL LANGSUNG DI SERVER (TANPA DOCKER) -->
        <div class="upload-panel">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
                <div>
                    <h3 style="margin:0; color:#1e3a8a;">📂 Pusat Update Data Langsung di Server (Tanpa Buka Docker)</h3>
                    <p style="margin:4px 0 0 0; font-size:0.84rem; color:#475569;">
                        Upload file <b>TARGET PER MONTH (.xlsx)</b> dan/atau <b>list_prospect (.xls / .xlsx / .csv)</b>, atau ubah tanggal berjalan. Perubahan langsung tersimpan permanen di server <code>laporantelesalesoxygen.my.id</code>.
                    </p>
                </div>
                <form method="post" style="margin:0;" onsubmit="return confirm('Kembalikan data server ke dataset default?');">
                    <input type="hidden" name="action" value="reset_default_data">
                    <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                    <button type="submit" class="btn btn-amber" style="padding:8px 14px; font-size:0.82rem;">♻️ Reset Dataset Default</button>
                </form>
            </div>

            <form method="post" enctype="multipart/form-data">
                <input type="hidden" name="action" value="upload_excel_data">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">

                <div class="grid-3">
                    <div>
                        <label style="font-size:0.83rem;"><b>1️⃣ Upload File Target (<code>.xlsx</code>) — Opsional:</b></label>
                        <input type="file" name="file_target" accept=".xlsx">
                        <div style="font-size:0.76rem; color:#475569; margin-top:-6px;">
                            Aktif di server: <b><?= htmlspecialchars((string)($sumberCur['target'] ?? 'TARGET PER MONTH.xlsx')) ?></b>
                        </div>
                    </div>
                    <div>
                        <label style="font-size:0.83rem;"><b>2️⃣ Upload File Prospect (<code>.xls</code> / <code>.xlsx</code> / <code>.csv</code>):</b></label>
                        <input type="file" name="file_prospect[]" accept=".xls,.xlsx,.csv,.tsv" multiple>
                        <div style="font-size:0.76rem; color:#475569; margin-top:-6px;">
                            Database server: <b><?= number_format((int)($sumberCur['total_baris_prospect'] ?? 0), 0, ',', '.') ?> baris unik</b>
                        </div>
                    </div>
                    <div>
                        <label style="font-size:0.83rem;"><b>3️⃣ Mode Update Data Prospect:</b></label>
                        <select name="mode_prospect">
                            <option value="merge" selected>🔗 Gabungkan &amp; Perbarui Baris Terbaru (Data Bulan Lalu Aman)</option>
                            <option value="replace">🔄 Ganti Total Hanya Dengan File yang Baru Diupload</option>
                        </select>
                    </div>
                </div>

                <div class="grid-4" style="margin-top:8px;">
                    <div>
                        <label style="font-size:0.81rem;"><b>Sheet File Target:</b></label>
                        <input type="text" name="sheet_name" value="<?= htmlspecialchars((string)($paramsCur['sheet'] ?? "NOVEMBER'26")) ?>" required>
                    </div>
                    <div>
                        <label style="font-size:0.81rem;"><b>Hari Berjalan (Cutoff MTD):</b></label>
                        <input type="number" name="hari_berjalan" min="1" max="31" value="<?= (int)($paramsCur['hari_berjalan'] ?? $hariBerjalan) ?>" required>
                    </div>
                    <div>
                        <label style="font-size:0.81rem;"><b>Tanggal Cek Blm Produktif:</b></label>
                        <input type="number" name="hari_harian" min="1" max="31" value="<?= (int)($paramsCur['hari_harian'] ?? $dailyDay) ?>" required>
                    </div>
                    <div>
                        <label style="font-size:0.81rem;"><b>Total Hari Kerja:</b></label>
                        <input type="number" name="total_hari" min="1" max="31" value="<?= (int)($paramsCur['total_hari'] ?? $totalHari) ?>" required>
                    </div>
                </div>

                <div class="grid-3">
                    <div>
                        <label style="font-size:0.81rem;"><b>Bulan Lalu (Pembanding 1-12):</b></label>
                        <input type="number" name="bulan_lalu" min="1" max="12" value="<?= (int)($paramsCur['bulan_lalu'] ?? 10) ?>" required>
                    </div>
                    <div>
                        <label style="font-size:0.81rem;"><b>Bulan Ini (Berjalan 1-12):</b></label>
                        <input type="number" name="bulan_ini" min="1" max="12" value="<?= (int)($paramsCur['bulan_ini'] ?? 11) ?>" required>
                    </div>
                    <div class="grid-2" style="gap:10px;">
                        <div>
                            <label style="font-size:0.81rem;"><b>Tahun:</b></label>
                            <input type="number" name="tahun" min="2023" max="2035" value="<?= (int)($paramsCur['tahun'] ?? 2026) ?>" required>
                        </div>
                        <div>
                            <label style="font-size:0.81rem;"><b>Rasio Paid/SA:</b></label>
                            <input type="number" step="0.05" name="rasio_paid" min="0.5" max="5.0" value="<?= htmlspecialchars((string)($paramsCur['rasio_paid'] ?? 1.25)) ?>" required>
                        </div>
                    </div>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
                    <div style="font-size:0.8rem; color:#334155;">
                        🕒 Update Server Terakhir: <b><?= htmlspecialchars((string)($sumberCur['updated_at'] ?? '-')) ?></b>
                        oleh <b><?= htmlspecialchars((string)($sumberCur['updated_by'] ?? 'System')) ?></b>
                    </div>
                    <button type="submit" class="btn btn-green" style="padding:12px 24px;">
                        🚀 Upload &amp; Update Semua Data ke Server Sekarang
                    </button>
                </div>
            </form>
        </div>
    <?php endif; ?>

    <?php if ($role === 'Agen' && !empty($authUser['agent_name'])):
        foreach ($agentRows as $ag) {
            if ($ag['name'] === $authUser['agent_name'] || (!empty($authUser['agent_key']) && $ag['agent_key'] === $authUser['agent_key'])) {
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
            <div class="metric-sub">Target MTD Hari ke-<?= $hariBerjalan ?>: <?= $targetMtd ?>%</div>
        </div>
        <div class="metric-box">
            <div class="metric-label">✅ Realisasi <?= htmlspecialchars($kolNov) ?></div>
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

    <div class="grid-2" style="align-items:start;">
        <!-- DASHBOARD 1: MTD SA -->
        <div class="card">
            <h3 style="margin-top:0;">📈 1. TABEL MTD SA PER LEADER (<?= htmlspecialchars($kolOct) ?> vs <?= htmlspecialchars($kolNov) ?>)</h3>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th>SALES LEADER</th>
                            <th><?= htmlspecialchars($kolOct) ?></th>
                            <th><?= htmlspecialchars($kolNov) ?></th>
                            <th>GAP SA</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php
                        $totOctDisp = 0; $totNovDisp = 0;
                        foreach ($mtdRows as $mr):
                            $isTot = strtoupper($mr['leader']) === 'TOTAL';
                            if ($isTot) {
                                $totOctDisp = (int)$mr['sa_oct'];
                                $totNovDisp = (int)$mr['sa_nov'];
                            }
                            if (!$isTot && $selectedScope !== 'Semua Leader' && $mr['leader'] !== $selectedScope) continue;
                            $gapCls = $mr['gap_sa'] < 0 ? 'gap-neg' : ($mr['gap_sa'] > 0 ? 'gap-pos' : '');
                        ?>
                            <tr class="<?= $isTot ? 'row-total' : '' ?>">
                                <td class="left"><?= htmlspecialchars($mr['leader']) ?></td>
                                <td><?= number_format($mr['sa_oct'], 0, ',', '.') ?></td>
                                <td><?= number_format($mr['sa_nov'], 0, ',', '.') ?></td>
                                <td class="<?= $gapCls ?>"><?= $mr['gap_sa'] ?></td>
                            </tr>
                        <?php endforeach;
                        $acvPctChange = $totOctDisp > 0 ? round((($totNovDisp - $totOctDisp) / $totOctDisp) * 100) : 0;
                        $acvArrow = $acvPctChange < 0 ? '↓' : ($acvPctChange > 0 ? '↑' : '→');
                        ?>
                        <tr style="background:#d9e1f2; font-weight:800;">
                            <td class="left" colspan="2">Note Acv SA</td>
                            <td><?= $acvArrow ?></td>
                            <td style="color:<?= $acvPctChange < 0 ? '#b91c1c' : '#166534' ?>;"><?= $acvPctChange ?>%</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- DASHBOARD 1B: REKAP HARIAN SO / PAID / SA & JUMLAH AGENT BLM PRODUKTIF -->
        <?php if ($role !== 'Agen'): ?>
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
                <h3 style="margin:0;">📊 1B. REKAP HARIAN &amp; AGENT BLM PRODUKTIF (<?= htmlspecialchars($dailyLbl) ?>)</h3>
                <form method="post" style="margin:0; display:flex; gap:6px; align-items:center;">
                    <input type="hidden" name="action" value="switch_daily_date">
                    <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                    <select name="hari_harian_cek" onchange="this.form.submit()" style="margin:0; width:auto; padding:6px 10px; font-size:0.84rem;">
                        <?php foreach ($tglTersedia as $tgNum): ?>
                            <option value="<?= (int)$tgNum ?>" <?= (int)$tgNum === $dailyDay ? 'selected' : '' ?>>
                                Tgl <?= (int)$tgNum ?> <?= htmlspecialchars($lblBlnIni) ?>
                            </option>
                        <?php endforeach; ?>
                    </select>
                </form>
            </div>
            <div class="table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th rowspan="2" class="navy-hdr">Sales Leader</th>
                            <th colspan="3" class="navy-hdr"><?= htmlspecialchars($dailyLbl) ?></th>
                            <th colspan="3" class="red-hdr">Jumlah Agent Blm Produktif</th>
                        </tr>
                        <tr>
                            <th class="navy-hdr">SO</th>
                            <th class="navy-hdr">PAID</th>
                            <th class="navy-hdr">SA</th>
                            <th class="red-hdr">SO</th>
                            <th class="red-hdr">PAID</th>
                            <th class="red-hdr">SA</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($dailyRows as $dr):
                            $isGt = !empty($dr['is_grand_total']) || strcasecmp($dr['leader'], 'Grand Total') === 0;
                            if ($isGt && $selectedScope !== 'Semua Leader') continue;
                            if (!$isGt && $selectedScope !== 'Semua Leader' && $dr['leader'] !== $selectedScope) continue;
                        ?>
                            <tr class="<?= $isGt ? 'row-grand' : '' ?>">
                                <td class="left"><?= htmlspecialchars($dr['leader']) ?></td>
                                <td><?= number_format((int)$dr['so'], 0, ',', '.') ?></td>
                                <td><?= number_format((int)$dr['paid'], 0, ',', '.') ?></td>
                                <td><?= number_format((int)$dr['sa'], 0, ',', '.') ?></td>
                                <td class="<?= $isGt ? 'peach-cell' : '' ?>"><?= (int)$dr['blm_so'] ?></td>
                                <td class="<?= $isGt ? 'peach-cell' : '' ?>"><?= (int)$dr['blm_paid'] ?></td>
                                <td class="<?= $isGt ? 'peach-cell' : '' ?>"><?= (int)$dr['blm_sa'] ?></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <details style="margin-top:10px; background:#f8fafc; padding:10px 12px; border-radius:8px; border:1px solid #cbd5e1;">
                <summary style="cursor:pointer; font-weight:700; font-size:0.85rem; color:#991b1b;">
                    🔎 Lihat Nama Agen Belum Produktif pada <?= htmlspecialchars($dailyLbl) ?> (0 SO / 0 PAID / 0 SA)
                </summary>
                <div style="margin-top:8px; font-size:0.8rem; line-height:1.5;">
                    <?php foreach ($dailyRows as $dr):
                        if (!empty($dr['is_grand_total'])) continue;
                        if ($selectedScope !== 'Semua Leader' && $dr['leader'] !== $selectedScope) continue;
                    ?>
                        <div style="margin-bottom:6px; padding-bottom:6px; border-bottom:1px dashed #cbd5e1;">
                            <b><?= htmlspecialchars($dr['leader']) ?></b> (<?= (int)$dr['total_agents'] ?> agen):<br>
                            • <b>0 SO (<?= (int)$dr['blm_so'] ?>)</b>: <?= htmlspecialchars(implode(', ', $dr['agents_blm_so'] ?? []) ?: 'Semua Produktif') ?><br>
                            • <b>0 PAID (<?= (int)$dr['blm_paid'] ?>)</b>: <?= htmlspecialchars(implode(', ', $dr['agents_blm_paid'] ?? []) ?: 'Semua Produktif') ?><br>
                            • <b>0 SA (<?= (int)$dr['blm_sa'] ?>)</b>: <?= htmlspecialchars(implode(', ', $dr['agents_blm_sa'] ?? []) ?: 'Semua Produktif') ?>
                        </div>
                    <?php endforeach; ?>
                </div>
            </details>
        </div>
        <?php endif; ?>
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
                        <th>SA <?= htmlspecialchars($lblBlnIni) ?></th>
                        <th>PAID <?= htmlspecialchars($lblBlnIni) ?></th>
                        <th>GAP SA <?= htmlspecialchars($lblBlnIni) ?></th>
                        <th>PERSENTASE</th>
                        <th>STATUS PERSENTASE</th>
                        <th>Harus Paid / Hari</th>
                        <th>Harus SA / Hari</th>
                        <th>RUNRATE <?= $totalHari ?> HARI</th>
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
                        $subRr = round(($subSa * $totalHari) / max(1, $hariBerjalan));
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

    <!-- DASHBOARD 2B: FOKUS AGEN YANG MASIH KURANG (< TARGET MTD %) -->
    <?php
    $kurangAgents = array_values(array_filter($filteredAgents, fn($r) => strtoupper($r['name']) !== 'VACANT' && $r['persen'] < $targetMtd));
    if (!empty($kurangAgents) && $role !== 'Agen'):
    ?>
    <div class="card">
        <h3 style="margin-top:0;">⚠️ 2B. FOKUS AGEN YANG MASIH KURANG (&lt; Target Berjalan MTD <?= $targetMtd ?>%) — <?= count($kurangAgents) ?> Agen</h3>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>SALES LEADER</th><th>SALES NAME</th><th>LEVEL</th><th>TARGET ALL</th>
                        <th>SA</th><th>PAID</th><th>% SAAT INI</th><th>KURANG KE MTD</th>
                        <th>HARUS PAID / HARI</th><th>HARUS SA / HARI</th><th>EST. KOMISI</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($kurangAgents as $kr): ?>
                        <tr>
                            <td class="left"><?= htmlspecialchars($kr['leader']) ?></td>
                            <td class="left"><b><?= htmlspecialchars($kr['name']) ?></b></td>
                            <td><?= htmlspecialchars($kr['level']) ?></td>
                            <td><?= $kr['target_all'] ?></td>
                            <td class="col-sa"><?= $kr['sa_nov'] ?></td>
                            <td><?= $kr['paid_nov'] ?></td>
                            <td class="col-pct"><?= $kr['persen'] ?>%</td>
                            <td><span class="status-kurang">-<?= ($targetMtd - $kr['persen']) ?>% (Kurang <?= (int)$kr['kurang_sa_mtd'] ?> SA)</span></td>
                            <td><b><?= $kr['harus_paid_hr'] ?> Paid/hr</b></td>
                            <td><b><?= $kr['harus_sa_hr'] ?> SA/hr</b> (<?= number_format($kr['harus_sa_des'], 1) ?>)</td>
                            <td class="left"><?= rp($kr['est_komisi']) ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
    <?php endif; ?>

    <!-- DASHBOARD 3: KIRIM LAPORAN KE BOT TELEGRAM -->
    <div class="card">
        <h3 style="margin-top:0;">📲 3. KIRIM LAPORAN LENGKAP KE BOT TELEGRAM</h3>
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
                <button type="submit" class="btn" style="width:100%; padding:12px;">🚀 Kirim Laporan Lengkap (<?= htmlspecialchars($selectedScope) ?>) ke Telegram</button>
            </div>
        </form>
    </div>
<?php endif; ?>
</div>
</body>
</html>
