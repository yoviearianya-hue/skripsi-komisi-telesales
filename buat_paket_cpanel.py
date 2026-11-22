"""Generator Paket Web cPanel Terproteksi WAF & Firewall + Live Excel Upload Engine
Domain Target: https://laporantelesalesoxygen.my.id

Menghasilkan paket siap-ekstrak untuk `public_html`:
1. .htaccess          (Firewall Apache, Security Headers, Blokir uploads/ & file sensitif, Upload 64MB)
2. engine.php         (Parser Excel .xlsx/.xls/.csv & Mesin Perhitungan MTD + Harian Blm Produktif)
3. index.php          (Portal Eksekutif Lengkap: WAF Dual Rate-Limiter, PBKDF2/SHA-256 Auth,
                       Tabel MTD SA, Tabel Harian SO/PAID/SA & Agent Blm Produktif, Detail Agent,
                       Fokus Agen < Target MTD, Upload Excel & Update Parameter Langsung di Server,
                       Brankas & Pengelola Password Semua Role, Download Laporan Excel/CSV, Telegram,
                       serta API Auto-Sync HTTPS tanpa Docker)
4. data_komisi.json   (Dataset JSON sinkron dengan `app.py` & `engine.php`)
5. uploads/           (Terproteksi `.htaccess` Deny All: target_active.xlsx, prospect_pool.json.gz,
                       roles_store.json [hanya hash + vault terenkripsi], superadmin_store.json)
6. UPLOAD_KE_CPANEL_PUBLIC_HTML.zip
"""

import json
import logging
import os
import shutil
import subprocess
import warnings
import zipfile

warnings.filterwarnings("ignore")
logging.disable(logging.WARNING)

import app as modul_app
import security_firewall as sf

FOLDER_PROYEK = os.path.dirname(os.path.abspath(__file__))
FOLDER_CPANEL = os.path.join(FOLDER_PROYEK, "cpanel_public_html")
FOLDER_UPLOADS = os.path.join(FOLDER_CPANEL, "uploads")
PATH_ENGINE_SRC = os.path.join(FOLDER_PROYEK, "cpanel_src", "engine.php")
PATH_ENGINE_ROOT = os.path.join(FOLDER_PROYEK, "engine.php")
PATH_ZIP = os.path.join(FOLDER_PROYEK, "UPLOAD_KE_CPANEL_PUBLIC_HTML.zip")
PHP_PORTABLE = r"C:\Users\yovie\.gemini\antigravity\brain\0eb9316b-02ba-4f62-91bd-5e1e85424634\scratch\php\php.exe"


def _copy_if_different(src: str, dst: str) -> None:
    if os.path.abspath(src) != os.path.abspath(dst):
        shutil.copy2(src, dst)


def buat_paket_cpanel() -> None:
    os.makedirs(FOLDER_CPANEL, exist_ok=True)
    os.makedirs(FOLDER_UPLOADS, exist_ok=True)

    # 1. Salin engine.php ke cpanel_public_html/engine.php & root engine.php
    path_engine_dst = os.path.join(FOLDER_CPANEL, "engine.php")
    _copy_if_different(PATH_ENGINE_SRC, path_engine_dst)
    _copy_if_different(PATH_ENGINE_SRC, PATH_ENGINE_ROOT)

    # 2. Salin TARGET PER MONTH.xlsx ke uploads/target_active.xlsx & default_target.xlsx
    src_target = os.path.join(FOLDER_PROYEK, "TARGET PER MONTH.xlsx")
    if os.path.isfile(src_target):
        shutil.copy2(src_target, os.path.join(FOLDER_UPLOADS, "target_active.xlsx"))
        shutil.copy2(src_target, os.path.join(FOLDER_UPLOADS, "default_target.xlsx"))

    # 3. Proteksi ketat direktori uploads/ dengan .htaccess
    htaccess_uploads = """Options -Indexes
<IfModule mod_authz_core.c>
    Require all denied
</IfModule>
<IfModule !mod_authz_core.c>
    Order allow,deny
    Deny from all
</IfModule>
"""
    with open(os.path.join(FOLDER_UPLOADS, ".htaccess"), "w", encoding="utf-8") as f:
        f.write(htaccess_uploads)

    # 4. Muat konfigurasi Super Admin & Roles (Hanya Hash + Vault Terenkripsi — Zero Plaintext!)
    cfg_sa = sf.muat_config_superadmin()
    if not cfg_sa:
        raise RuntimeError("superadmin_config.json belum ditemukan!")
    cfg_roles = sf.muat_config_roles()
    if not cfg_roles:
        raise RuntimeError("roles_config.json belum ditemukan!")

    with open(os.path.join(FOLDER_UPLOADS, "superadmin_store.json"), "w", encoding="utf-8") as f:
        json.dump(cfg_sa, f, ensure_ascii=False, indent=2)
    with open(os.path.join(FOLDER_UPLOADS, "roles_store.json"), "w", encoding="utf-8") as f:
        json.dump(cfg_roles, f, ensure_ascii=False, indent=2)

    # 5. Hitung payload default lewat `engine.php` (memastikan 100% sinkronisasi PHP <-> Python)
    hari_def = int(modul_app.hari_berjalan_int)
    bln_lalu_def = int(modul_app.bulan_lalu_int)
    bln_ini_def = int(modul_app.bulan_ini_int)
    tahun_def = int(modul_app.tahun_int)
    tot_hari_def = int(modul_app.total_hari_int)
    rasio_def = float(modul_app.rasio_paid_float)
    sheet_def = str(modul_app.nama_sheet_target)

    pool_path = os.path.join(FOLDER_UPLOADS, "prospect_pool.json.gz").replace("\\", "/")
    def_pool_path = os.path.join(FOLDER_UPLOADS, "default_prospect_pool.json.gz").replace("\\", "/")
    path_json = os.path.join(FOLDER_CPANEL, "data_komisi.json").replace("\\", "/")
    def_json_path = os.path.join(FOLDER_UPLOADS, "default_data_komisi.json").replace("\\", "/")
    proy_slash = FOLDER_PROYEK.replace("\\", "/")

    if not os.path.isfile(PHP_PORTABLE):
        raise RuntimeError(f"PHP CLI tidak ditemukan di {PHP_PORTABLE}")

    php_build_script = (
        f"define('APP_BOOT', true); "
        f"require '{path_engine_dst.replace(chr(92), '/')}'; "
        f"$res = proses_data(["
        f"'target_path' => '{proy_slash}/TARGET PER MONTH.xlsx', "
        f"'sheet' => " + json.dumps(sheet_def) + ", "
        f"'prospects' => ["
        f"['path' => '{proy_slash}/list_prospect September.xls', 'name' => 'list_prospect September.xls'], "
        f"['path' => '{proy_slash}/list_prospect Oktober.xls', 'name' => 'list_prospect Oktober.xls'], "
        f"['path' => '{proy_slash}/list_prospect November.xls', 'name' => 'list_prospect November.xls']"
        f"], "
        f"'bulan_lalu' => {bln_lalu_def}, 'bulan_ini' => {bln_ini_def}, 'tahun' => {tahun_def}, "
        f"'total_hari' => {tot_hari_def}, 'hari_berjalan' => {hari_def}, 'hari_harian' => {hari_def}, 'hari_wo' => {hari_def}, "
        f"'rasio_paid' => {rasio_def}, "
        f"'simpan_pool_path' => '{pool_path}'"
        f"]); "
        f"$res['bot_token_default'] = '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs'; "
        f"$res['docker_tunnel_url'] = " + json.dumps(modul_app.ambil_url_publik_aktif()) + "; "
        f"$res['sumber']['updated_at'] = date('Y-m-d H:i:s'); "
        f"$res['sumber']['updated_by'] = 'Paket Server Terbaru'; "
        f"file_put_contents('{path_json}', json_encode($res, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE)); "
        f"copy('{path_json}', '{def_json_path}'); "
        f"copy('{pool_path}', '{def_pool_path}');"
    )
    subprocess.run([PHP_PORTABLE, "-r", php_build_script], check=True)

    # 6. Tulis .htaccess utama (Firewall Berlapis, Security Headers) & .user.ini (LiteSpeed / PHP-FPM Limits)
    path_user_ini = os.path.join(FOLDER_CPANEL, ".user.ini")
    with open(path_user_ini, "w", encoding="utf-8") as f:
        f.write(
            "upload_max_filesize = 64M\n"
            "post_max_size = 64M\n"
            "memory_limit = 768M\n"
            "max_execution_time = 180\n"
            "max_input_time = 180\n"
        )
    kode_htaccess = r"""# ==============================================================================
# SERVER FIREWALL & WAF (.htaccess) — laporantelesalesoxygen.my.id
# ==============================================================================

Options -Indexes
ServerSignature Off

# 1. Blokir Akses Publik Langsung ke File Data, Konfigurasi, Log & Engine
<FilesMatch "\.(json|gz|xlsx|xls|csv|tsv|sql|log|ini|env|bak|sh|py|zip|md)$">
    <IfModule mod_authz_core.c>
        Require all denied
    </IfModule>
    <IfModule !mod_authz_core.c>
        Order allow,deny
        Deny from all
    </IfModule>
</FilesMatch>

<Files "engine.php">
    <IfModule mod_authz_core.c>
        Require all denied
    </IfModule>
    <IfModule !mod_authz_core.c>
        Order allow,deny
        Deny from all
    </IfModule>
</Files>

# 2. HTTP Security Headers (Anti-Clickjacking, Anti-XSS, Anti-MIME Sniffing)
<IfModule mod_headers.c>
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set X-Content-Type-Options "nosniff"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Permissions-Policy "geolocation=(), microphone=(), camera=()"
    Header always set Content-Security-Policy "frame-ancestors 'self';"
</IfModule>

# 3. WAF Rewrite Rules (Blokir folder uploads/, SQLi, XSS & Path Traversal)
<IfModule mod_rewrite.c>
    RewriteEngine On
    RewriteRule ^uploads/ - [F,L]
    RewriteCond %{QUERY_STRING} (\<|%3C).*script.*(\>|%3E) [NC,OR]
    RewriteCond %{QUERY_STRING} (union.*select|insert.*into|drop.*table|concat\(|information_schema) [NC,OR]
    RewriteCond %{QUERY_STRING} (\.\./|\.\.\\|/etc/passwd|boot\.ini) [NC]
    RewriteRule ^(.*)$ - [F,L]
</IfModule>

# 4. Kapasitas Upload File Excel Besar (hingga 64MB)
<IfModule mod_php.c>
    php_value upload_max_filesize 64M
    php_value post_max_size 64M
    php_value memory_limit 512M
    php_value max_execution_time 300
</IfModule>
"""
    path_htaccess = os.path.join(FOLDER_CPANEL, ".htaccess")
    with open(path_htaccess, "w", encoding="utf-8") as f:
        f.write(kode_htaccess.strip() + "\n")

    # 7. Tulis index.php (Lengkap, Mandiri di Server tanpa Docker, Tanpa Celah)
    kode_php = r"""<?php
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
// Bebaskan exclusive session file lock segera agar reload / multi-tab tidak pernah "loading terus"
if ($_SERVER['REQUEST_METHOD'] !== 'POST' && !isset($_GET['logout'])) {
    @session_write_close();
}

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
    'username'   => '__SA_USER__',
    'salt'       => '__SA_SALT__',
    'iterations' => __SA_ITER__,
    'hash'       => '__SA_HASH__',
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

function send_telegram_server(string $botToken, string $chatId, string $text): array {
    $urlTg = "https://api.telegram.org/bot{$botToken}/sendMessage";
    $postBody = http_build_query([
        'chat_id'                  => $chatId,
        'text'                     => $text,
        'parse_mode'               => 'HTML',
        'disable_web_page_preview' => 'true',
    ]);

    $lastErr = '';
    if (function_exists('curl_init')) {
        foreach ([true, false] as $idxTry => $verifySsl) {
            $ch = curl_init($urlTg);
            $opts = [
                CURLOPT_POST           => true,
                CURLOPT_POSTFIELDS     => $postBody,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_CONNECTTIMEOUT => 3,
                CURLOPT_TIMEOUT        => 7,
                CURLOPT_SSL_VERIFYPEER => $verifySsl,
                CURLOPT_SSL_VERIFYHOST => $verifySsl ? 2 : 0,
                CURLOPT_HTTPHEADER     => ['Content-Type: application/x-www-form-urlencoded'],
            ];
            if (defined('CURL_IPRESOLVE_V4')) {
                $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
            }
            if (defined('CURL_HTTP_VERSION_1_1')) {
                $opts[CURLOPT_HTTP_VERSION] = CURL_HTTP_VERSION_1_1;
            }
            curl_setopt_array($ch, $opts);
            $resp = curl_exec($ch);
            $errno = curl_errno($ch);
            $err = curl_error($ch);
            $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
            curl_close($ch);

            if ($resp !== false && $httpCode > 0) {
                $j = json_decode((string)$resp, true);
                $desc = is_array($j) ? (string)($j['description'] ?? $resp) : (string)$resp;
                return [
                    'ok'          => ($httpCode === 200 && is_array($j) && !empty($j['ok'])),
                    'http_code'   => $httpCode,
                    'description' => $desc,
                    'error'       => $desc,
                    'method'      => $verifySsl ? 'cURL' : 'cURL-NoCA',
                ];
            }
            $lastErr = "cURL #{$errno}: " . ($err ?: 'Koneksi server diblokir/timeout');
            // Hanya coba ulang tanpa verify SSL jika memang error sertifikat CA lokal
            if ($idxTry === 0 && !in_array($errno, [35, 51, 58, 60, 77], true)) {
                break;
            }
        }
    } else {
        $lastErr = 'Ekstensi cURL PHP tidak aktif';
    }

    // Fallback ke PHP stream HTTPS jika cURL gagal HTTP 0 dan allow_url_fopen aktif
    if (ini_get('allow_url_fopen')) {
        $ctx = stream_context_create([
            'http' => [
                'method'           => 'POST',
                'header'           => "Content-Type: application/x-www-form-urlencoded\r\n",
                'content'          => $postBody,
                'timeout'          => 5,
                'ignore_errors'    => true,
                'protocol_version' => 1.1,
            ],
            'ssl' => [
                'verify_peer'      => false,
                'verify_peer_name' => false,
            ],
        ]);
        $streamResp = @file_get_contents($urlTg, false, $ctx);
        $streamCode = 0;
        if (!empty($http_response_header) && preg_match('/\s(\d{3})\s/', (string)$http_response_header[0], $hm)) {
            $streamCode = (int)$hm[1];
        }
        if ($streamResp !== false && $streamCode > 0) {
            $j = json_decode($streamResp, true);
            $desc = is_array($j) ? (string)($j['description'] ?? $streamResp) : $streamResp;
            return [
                'ok'          => ($streamCode === 200 && is_array($j) && !empty($j['ok'])),
                'http_code'   => $streamCode,
                'description' => $desc,
                'error'       => $desc,
                'method'      => 'PHP-Stream',
            ];
        }
        $lastErr .= ' | Stream gagal terhubung';
    }

    return [
        'ok'          => false,
        'http_code'   => 0,
        'description' => $lastErr,
        'error'       => $lastErr,
        'method'      => 'blocked',
    ];
}

function send_telegram_server_file(string $botToken, string $chatId, string $filePath, string $fileName, string $caption, string $imgMode = 'photo'): array {
    if (!function_exists('curl_init') || !class_exists('CURLFile')) {
        return ['ok' => false, 'http_code' => 0, 'description' => 'cURL/CURLFile tidak aktif di PHP'];
    }
    $endpoint = ($imgMode === 'document') ? 'sendDocument' : 'sendPhoto';
    $field = ($imgMode === 'document') ? 'document' : 'photo';
    $urlTg = "https://api.telegram.org/bot{$botToken}/{$endpoint}";

    foreach ([true, false] as $idxTry => $verifySsl) {
        $ch = curl_init($urlTg);
        $opts = [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => [
                'chat_id'    => $chatId,
                'caption'    => $caption,
                'parse_mode' => 'HTML',
                $field       => new CURLFile($filePath, 'image/png', $fileName),
            ],
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_CONNECTTIMEOUT => 4,
            CURLOPT_TIMEOUT        => 12,
            CURLOPT_SSL_VERIFYPEER => $verifySsl,
            CURLOPT_SSL_VERIFYHOST => $verifySsl ? 2 : 0,
        ];
        if (defined('CURL_IPRESOLVE_V4')) $opts[CURLOPT_IPRESOLVE] = CURL_IPRESOLVE_V4;
        if (defined('CURL_HTTP_VERSION_1_1')) $opts[CURLOPT_HTTP_VERSION] = CURL_HTTP_VERSION_1_1;
        curl_setopt_array($ch, $opts);
        $resp = curl_exec($ch);
        $errno = curl_errno($ch);
        $err = curl_error($ch);
        $httpCode = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($resp !== false && $httpCode > 0) {
            $j = json_decode((string)$resp, true);
            $desc = is_array($j) ? (string)($j['description'] ?? $resp) : (string)$resp;
            return ['ok' => ($httpCode === 200 && is_array($j) && !empty($j['ok'])), 'http_code' => $httpCode, 'description' => $desc];
        }
        if ($idxTry === 0 && !in_array($errno, [35, 51, 58, 60, 77], true)) {
            return ['ok' => false, 'http_code' => 0, 'description' => "cURL #{$errno}: " . ($err ?: 'timeout/blocked')];
        }
    }
    return ['ok' => false, 'http_code' => 0, 'description' => 'Server gagal upload file ke Telegram'];
}

function build_tg_visual_payload(array $appData, string $scopeSend, bool $includeWo = true, bool $includeWoCards = false, string $onlyAgent = ''): array {
    $agentRowsTg = $appData['agent_rows'] ?? [];
    $mtdRowsTg   = $appData['mtd_rows'] ?? [];
    $dailyRowsTg = $appData['daily_prod_rows'] ?? [];

    if ($onlyAgent !== '') {
        $wsSrc = $appData['wo_summary'] ?? [];
        $onlyKey = normalisasi_nama_agen($onlyAgent);
        $agOnly = [];
        foreach (($wsSrc['agent_summary'] ?? []) as $ar) {
            if (normalisasi_nama_agen($ar['salesname'] ?? '') === $onlyKey) {
                $agOnly[] = $ar;
            }
        }
        return [
            'scope' => $scopeSend,
            'only_agent' => $onlyAgent,
            'wo_summary' => [
                'today_label'   => (string)($wsSrc['today_label'] ?? ''),
                'besok_label'   => (string)($wsSrc['besok_label'] ?? ''),
                'agent_summary' => $agOnly,
            ],
        ];
    }

    $mtdFiltered = [];
    foreach ($mtdRowsTg as $mr) {
        $isTot = strtoupper((string)$mr['leader']) === 'TOTAL';
        if ($isTot || $scopeSend === 'Semua Leader' || $mr['leader'] === $scopeSend) {
            $mtdFiltered[] = [
                'leader' => (string)$mr['leader'],
                'sa_oct' => (int)$mr['sa_oct'],
                'sa_nov' => (int)$mr['sa_nov'],
                'gap_sa' => (int)$mr['gap_sa'],
                'is_total' => $isTot,
            ];
        }
    }

    $dailyFiltered = [];
    foreach ($dailyRowsTg as $dr) {
        $isGt = !empty($dr['is_grand_total']) || strcasecmp((string)$dr['leader'], 'Grand Total') === 0;
        if (($isGt && $scopeSend === 'Semua Leader') || (!$isGt && ($scopeSend === 'Semua Leader' || $dr['leader'] === $scopeSend))) {
            $dailyFiltered[] = [
                'leader'            => (string)$dr['leader'],
                'so'                => (int)$dr['so'],
                'gp'                => (int)($dr['gp'] ?? 0),
                'paid'              => (int)$dr['paid'],
                'sa'                => (int)$dr['sa'],
                'blm_so'            => (int)$dr['blm_so'],
                'blm_paid'          => (int)$dr['blm_paid'],
                'blm_sa'            => (int)$dr['blm_sa'],
                'sudah_paid_agents' => (int)($dr['sudah_paid_agents'] ?? 0),
                'sudah_gp_agents'   => (int)($dr['sudah_gp_agents'] ?? 0),
                'agents_paid'       => array_values($dr['agents_paid'] ?? []),
                'agents_gp'         => array_values($dr['agents_gp'] ?? []),
                'agents_tidak_paid' => array_values($dr['agents_tidak_paid'] ?? []),
                'agent_details'     => array_values($dr['agent_details'] ?? []),
                'is_gt'             => $isGt,
            ];
        }
    }

    // Hanya menyertakan TARGET ALL (tanpa Reguler/Yearly terpisah sesuai RBAC Telegram)
    $agentsSafe = [];
    foreach ($agentRowsTg as $ag) {
        if ($scopeSend !== 'Semua Leader' && $ag['leader'] !== $scopeSend) continue;
        $agentsSafe[] = [
            'leader'          => (string)$ag['leader'],
            'name'            => (string)$ag['name'],
            'level'           => (string)$ag['level'],
            'target_all'      => (int)$ag['target_all'],
            'sa_nov'          => (int)$ag['sa_nov'],
            'paid_nov'        => (int)$ag['paid_nov'],
            'gap_sa'          => (int)$ag['gap_sa'],
            'persen'          => (int)$ag['persen'],
            'runrate_30'      => (int)$ag['runrate_30'],
            'p_m'             => (int)$ag['p_m'],
            'p_3m'            => (int)$ag['p_3m'],
            'p_sem'           => (int)$ag['p_sem'],
            'p_yr'            => (int)$ag['p_yr'],
            'harus_paid_hr'   => (int)$ag['harus_paid_hr'],
            'harus_sa_hr'     => (int)$ag['harus_sa_hr'],
            'tier_komisi'     => (string)($ag['tier_komisi'] ?? 'Tier 0 (0%)'),
            'rev_fp'          => (float)($ag['rev_fp'] ?? ($ag['rev_netto'] ?? 0)),
            'insentif_fp'     => (float)($ag['insentif_fp'] ?? 0),
            'insentif_yearly' => (float)($ag['insentif_yearly'] ?? 0),
            'est_komisi'      => (float)($ag['est_komisi'] ?? 0),
        ];
    }

    $woSafe = null;
    if ($includeWo && !empty($appData['wo_summary']['leader_summary'])) {
        $wsSrc = $appData['wo_summary'];
        $woLdrRows = [];
        foreach ($wsSrc['leader_summary'] as $wr) {
            $isGtW = !empty($wr['is_grand_total']) || strcasecmp((string)($wr['leader'] ?? ''), 'Grand Total') === 0;
            if ($isGtW && $scopeSend !== 'Semua Leader') continue;
            if (!$isGtW && $scopeSend !== 'Semua Leader' && ($wr['leader'] ?? '') !== $scopeSend) continue;
            $woLdrRows[] = [
                'leader'                => (string)($wr['leader'] ?? ''),
                'today_sa'              => (int)($wr['today_sa'] ?? 0),
                'today_on_installation' => (int)($wr['today_on_installation'] ?? 0),
                'today_reschedule'      => (int)($wr['today_reschedule'] ?? 0),
                'today_waiting_wo'      => (int)($wr['today_waiting_wo'] ?? 0),
                'today_refund'          => (int)($wr['today_refund'] ?? 0),
                'today_other'           => (int)($wr['today_other'] ?? 0),
                'today_total'           => (int)($wr['today_total'] ?? 0),
                'wo_besok'              => (int)($wr['wo_besok'] ?? 0),
                'waiting_wo'            => (int)($wr['waiting_wo'] ?? 0),
                'is_gt'                 => $isGtW,
            ];
        }
        $filtWoScopeTg = static function (array $r) use ($scopeSend): bool {
            $rt = (string)($r['row_type'] ?? '');
            $isGt = ($rt === 'grand_total') || !empty($r['is_grand_total']) || strcasecmp((string)($r['leader'] ?? ''), 'Grand Total') === 0;
            if ($isGt) return $scopeSend === 'Semua Leader';
            return $scopeSend === 'Semua Leader' || ((string)($r['leader'] ?? '') === $scopeSend);
        };
        $woTodaySafe = array_values(array_filter($wsSrc['wo_today_rows'] ?? [], $filtWoScopeTg));
        $woWaitSafe  = array_values(array_filter($wsSrc['waiting_wo_rows'] ?? [], $filtWoScopeTg));
        $woBesokSafe = array_values(array_filter($wsSrc['wo_besok_rows'] ?? [], $filtWoScopeTg));
        $woAgSafe    = array_values(array_filter($wsSrc['agent_summary'] ?? [], $filtWoScopeTg));
        $woSafe = [
            'today_label'       => (string)($wsSrc['today_label'] ?? ''),
            'besok_label'       => (string)($wsSrc['besok_label'] ?? ''),
            'besok_range_label' => (string)($wsSrc['besok_range_label'] ?? ('>= ' . (string)($wsSrc['besok_label'] ?? ''))),
            'wo_today_columns'  => array_values($wsSrc['wo_today_columns'] ?? []),
            'leader_summary'    => $woLdrRows,
            'wo_today_rows'     => $woTodaySafe,
            'waiting_wo_rows'   => $woWaitSafe,
            'wo_besok_rows'     => $woBesokSafe,
            'agent_summary'     => $woAgSafe,
            'include_cards'     => $includeWoCards,
        ];
    }

    return [
        'scope'        => $scopeSend,
        'periode'      => (string)($appData['periode_label'] ?? ''),
        'target_mtd'   => (int)($appData['target_persen_mtd'] ?? 73),
        'hari'         => (int)($appData['hari_berjalan'] ?? 22),
        'total_hari'   => (int)($appData['total_hari'] ?? 30),
        'sisa_hari'    => (int)($appData['sisa_hari'] ?? 8),
        'bln_lalu'     => (string)($appData['label_bulan_lalu'] ?? 'OCT'),
        'bln_ini'      => (string)($appData['label_bulan_ini'] ?? 'NOV'),
        'tahun'        => (int)($appData['params']['tahun'] ?? 2026),
        'rasio_paid'   => (float)($appData['params']['rasio_paid'] ?? 1.25),
        'daily_label'  => (string)($appData['daily_prod_date_label'] ?? ''),
        'mtd_rows'     => $mtdFiltered,
        'daily_rows'   => $dailyFiltered,
        'wo_summary'   => $woSafe,
        'agent_rows'   => $agentsSafe,
    ];
}

function rp($angka): string {
    return 'Rp ' . number_format((float)$angka, 0, ',', '.');
}

function ensure_wo_summary_v2(array &$appData, string $poolActiveFile, string $poolDefaultFile, string $dataFile, string $targetActiveFile = '', string $targetDefaultFile = ''): void {
    $needsRecalc = (int)($appData['calc_engine_version'] ?? 0) < 4;
    $needsWoV2   = (int)($appData['wo_summary']['calc_version'] ?? 0) < 2;
    if (empty($appData['params']) || (!$needsRecalc && !$needsWoV2)) {
        return;
    }
    try {
        $poolAuto = load_prospect_pool($poolActiveFile, $poolDefaultFile);
        if (!$poolAuto) return;
        $cleanMap  = deduplikasi_pool_rows($poolAuto);
        $cleanPool = array_values($cleanMap);
        $pAuto = $appData['params'];
        $bLaluA = (int)($pAuto['bulan_lalu'] ?? 10);
        $bIniA  = (int)($pAuto['bulan_ini'] ?? 11);
        $thnA   = (int)($pAuto['tahun'] ?? 2026);
        $tHariA = (int)($pAuto['total_hari'] ?? 30);
        $hJlnA  = (int)($pAuto['hari_berjalan'] ?? ($appData['hari_berjalan'] ?? 22));
        $hHarA  = (int)($pAuto['hari_harian'] ?? ($appData['daily_prod_day'] ?? $hJlnA));
        $hWoA   = (int)($appData['wo_summary']['day'] ?? ($pAuto['hari_wo'] ?? $hHarA));
        $rasioA = (float)($pAuto['rasio_paid'] ?? 1.25);
        $sheetA = (string)($pAuto['sheet'] ?? "NOVEMBER'26");

        $tAct = $targetActiveFile !== '' ? $targetActiveFile : (__DIR__ . '/uploads/target_active.xlsx');
        $tDef = $targetDefaultFile !== '' ? $targetDefaultFile : (__DIR__ . '/uploads/default_target.xlsx');
        if (!file_exists($tAct) && file_exists($tDef)) {
            @copy($tDef, $tAct);
        }

        if ($needsRecalc && file_exists($tAct)) {
            $oldSumber   = $appData['sumber'] ?? [];
            $oldBot      = $appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs';
            $oldTunnel   = $appData['docker_tunnel_url'] ?? '';
            $recalc = proses_data([
                'target_path'        => $tAct,
                'target_name'        => (string)($oldSumber['target'] ?? 'TARGET PER MONTH.xlsx'),
                'sheet'              => $sheetA,
                'prospect_rows_awal' => $cleanPool,
                'prospects'          => [],
                'bulan_lalu'         => $bLaluA,
                'bulan_ini'          => $bIniA,
                'tahun'              => $thnA,
                'total_hari'         => $tHariA,
                'hari_berjalan'      => $hJlnA,
                'hari_harian'        => $hHarA,
                'hari_wo'            => $hWoA,
                'rasio_paid'         => $rasioA,
                'simpan_pool_path'   => $poolActiveFile,
            ]);
            if (!empty($oldSumber['prospect'])) {
                $recalc['sumber']['prospect'] = $oldSumber['prospect'];
            }
            $recalc['sumber']['updated_at'] = $oldSumber['updated_at'] ?? date('Y-m-d H:i:s');
            $recalc['sumber']['updated_by'] = $oldSumber['updated_by'] ?? 'Auto-Clean Engine v4';
            $recalc['bot_token_default'] = $oldBot;
            $recalc['docker_tunnel_url'] = $oldTunnel;
            $appData = $recalc;
        } else {
            if (count($cleanPool) !== count($poolAuto) && $poolActiveFile !== '') {
                @file_put_contents($poolActiveFile, gzencode(json_encode($cleanPool, JSON_UNESCAPED_UNICODE), 6), LOCK_EX);
            }
            $appData['wo_summary'] = hitung_wo_laporan($cleanPool, $bIniA, $thnA, $hWoA);
            $appData['params']['hari_wo'] = $appData['wo_summary']['day'];
            $appData['calc_engine_version'] = 4;
        }
        @file_put_contents($dataFile, json_encode($appData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX);
    } catch (Throwable $e) {
        // Lewati jika pool/target belum siap agar dashboard tetap merender aman
    }
}

// Muat Konfigurasi Awal
$saCfg    = get_superadmin_cfg($superAdminStoreFile, $superAdminFallback);
$rolesCfg = get_roles_cfg($rolesStoreFile);
$appData  = load_json_safe($dataFile, []);

$loginError   = '';
$actionStatus = '';
$tgStatus     = '';

// ============================================================================
// ENDPOINT UPLOAD GAMBAR PNG RELAY -> SERVER PHP (CADANGAN JIKA BROWSER DIBLOKIR)
// ============================================================================
if ($_SERVER['REQUEST_METHOD'] === 'POST' && ($_POST['action'] ?? '') === 'send_telegram_blob') {
    header('Content-Type: application/json; charset=utf-8');
    $curRole = $_SESSION['auth_user']['role'] ?? '';
    if (empty($_SESSION['auth_user']) || !in_array($curRole, ['Admin', 'Finance', 'Leader'], true)) {
        http_response_code(403);
        echo json_encode(['ok' => false, 'description' => 'Akses ditolak']);
        exit;
    }
    if (!hash_equals($csrfToken, (string)($_POST['csrf_token'] ?? ''))) {
        http_response_code(403);
        echo json_encode(['ok' => false, 'description' => 'CSRF token tidak valid']);
        exit;
    }
    $chatId  = trim((string)($_POST['chat_id'] ?? ''));
    $caption = (string)($_POST['caption'] ?? '');
    $imgMode = ($_POST['img_mode'] ?? 'photo') === 'document' ? 'document' : 'photo';
    $botTok  = (string)($_SESSION['tg_last_bot_token'] ?? ($appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs'));
    list($okChat, $msgChat) = waf_inspect_input($chatId, $auditLogFile);
    if (!$okChat || $chatId === '') {
        http_response_code(400);
        echo json_encode(['ok' => false, 'description' => $okChat ? 'Chat ID kosong' : $msgChat]);
        exit;
    }
    if (empty($_FILES['png_file']['tmp_name']) || $_FILES['png_file']['error'] !== UPLOAD_ERR_OK) {
        http_response_code(400);
        echo json_encode(['ok' => false, 'description' => 'File gambar PNG tidak diterima server']);
        exit;
    }
    $headBytes = (string)@file_get_contents($_FILES['png_file']['tmp_name'], false, null, 0, 8);
    if ($headBytes !== "\x89PNG\r\n\x1a\n") {
        http_response_code(400);
        echo json_encode(['ok' => false, 'description' => 'File bukan format PNG valid']);
        exit;
    }
    $fname = basename((string)($_FILES['png_file']['name'] ?? 'laporan.png'));
    @session_write_close();
    $resF = send_telegram_server_file($botTok, $chatId, $_FILES['png_file']['tmp_name'], $fname, $caption, $imgMode);
    if (!$resF['ok'] && $imgMode === 'photo' && $resF['http_code'] === 400 && stripos((string)$resF['description'], 'chat not found') === false) {
        $resF = send_telegram_server_file($botTok, $chatId, $_FILES['png_file']['tmp_name'], $fname, $caption, 'document');
    }
    echo json_encode($resF);
    exit;
}

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
        $hWo     = max(1, min(31, (int)($_POST['hari_wo'] ?? $hHarian)));
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
            'hari_wo'            => $hWo,
            'rasio_paid'         => $rasio,
            'simpan_pool_path'   => $poolActiveFile,
        ]);
        foreach ($tmpClean as $tf) @unlink($tf);

        $hasil['bot_token_default'] = $appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs';
        $hasil['docker_tunnel_url'] = $appData['docker_tunnel_url'] ?? '';
        $hasil['sumber']['updated_at'] = date('Y-m-d H:i:s');
        $hasil['sumber']['updated_by'] = $apiU . ' (Auto-Sync Server)';
        file_put_contents($dataFile, json_encode($hasil, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX);
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
    ensure_wo_summary_v2($appData, $poolActiveFile, $poolDefaultFile, $dataFile, $targetActiveFile, $targetDefaultFile);
    $dlType = $_GET['download'];
    $authU = $_SESSION['auth_user'];
    @session_write_close();
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
        array_push($hdr, 'SA', 'PAID', 'SO', 'GAP SA', 'PERSENTASE', 'STATUS MTD', 'Harus Paid / Hari', 'Harus SA / Hari', 'RUNRATE', '3 Monthly', 'Monthly', 'Semesterly', 'Yearly', 'Tier Komisi', 'Rev. FP (Excl. PPn)', 'Insentif FP', 'Ins. Yearly', 'Estimasi Komisi');
        fputcsv($out, $hdr);
        foreach ($dlAgents as $r) {
            $row = [$r['leader'], $r['name'], $r['masa_kerja'], $r['level'], $r['target_all']];
            if ($dlAdmin) { $row[] = $r['target_reguler']; $row[] = $r['target_yearly']; }
            array_push($row, $r['sa_nov'], $r['paid_nov'], $r['so_nov'], $r['gap_sa'], $r['persen'] . '%', $r['status_mtd'], $r['harus_paid_hr'], $r['harus_sa_hr'], $r['runrate_30'], $r['p_3m'], $r['p_m'], $r['p_sem'], $r['p_yr'], ($r['tier_komisi'] ?? 'Tier 0 (0%)'), round((float)($r['rev_fp'] ?? ($r['rev_netto'] ?? 0)), 0), (float)($r['insentif_fp'] ?? 0), (float)($r['insentif_yearly'] ?? 0), $r['est_komisi']);
            fputcsv($out, $row);
        }
        fclose($out);
        exit;
    }
    if ($dlType === 'excel') {
        header('Content-Type: application/vnd.ms-excel; charset=utf-8');
        header("Content-Disposition: attachment; filename=\"Laporan_Lengkap_Telesales_{$safeName}_{$lblP}.xls\"");
        echo '<html><meta charset="UTF-8"><body>';
        echo '<h3>1. REKAP HARIAN (' . htmlspecialchars($appData['daily_prod_date_label'] ?? '') . ') &amp; JUMLAH AGENT BLM PRODUKTIF</h3><table border="1"><tr><th>Sales Leader</th><th>SO</th><th>GP</th><th>PAID</th><th>SA</th><th>Blm Produktif SO</th><th>Blm Produktif PAID</th><th>Blm Produktif SA</th></tr>';
        foreach (($appData['daily_prod_rows'] ?? []) as $dr) {
            if (!empty($dr['is_grand_total']) && $dlScope !== 'Semua Leader') continue;
            if (empty($dr['is_grand_total']) && $dlScope !== 'Semua Leader' && $dr['leader'] !== $dlScope) continue;
            $dpGp = (int)($dr['gp'] ?? 0);
            echo '<tr><td>' . htmlspecialchars($dr['leader']) . "</td><td>{$dr['so']}</td><td>{$dpGp}</td><td>{$dr['paid']}</td><td>{$dr['sa']}</td><td>{$dr['blm_so']}</td><td>{$dr['blm_paid']}</td><td>{$dr['blm_sa']}</td></tr>";
        }
        echo '</table><br><h3>1B2. RINCIAN HARIAN PER AGENT (' . htmlspecialchars($appData['daily_prod_date_label'] ?? '') . ' — SUDAH PAID / SUDAH GP / TIDAK PAID)</h3><table border="1"><tr><th>Sales Leader</th><th>Salesname</th><th>SO</th><th>GP</th><th>PAID</th><th>Belum Paid (SO)</th><th>SA</th><th>Status Harian</th></tr>';
        foreach (($appData['daily_prod_rows'] ?? []) as $dr) {
            if (!empty($dr['is_grand_total'])) continue;
            if ($dlScope !== 'Semua Leader' && $dr['leader'] !== $dlScope) continue;
            foreach (($dr['agent_details'] ?? []) as $ad) {
                echo '<tr><td>' . htmlspecialchars((string)$ad['leader']) . '</td><td>' . htmlspecialchars((string)$ad['name']) . "</td><td>{$ad['so']}</td><td>{$ad['gp']}</td><td>{$ad['paid']}</td><td>{$ad['tidak_paid_so']}</td><td>{$ad['sa']}</td><td>" . htmlspecialchars((string)$ad['status_harian']) . '</td></tr>';
            }
        }
        $dlWoSum = $appData['wo_summary'] ?? [];
        if (!empty($dlWoSum['leader_summary'])) {
            echo '</table><br><h3>1C. MONITORING WORK ORDER (1. WO TODAY ' . htmlspecialchars((string)($dlWoSum['today_label'] ?? '')) . ' &amp; SA | 2. WO BESOK ' . htmlspecialchars((string)($dlWoSum['besok_range_label'] ?? ($dlWoSum['besok_label'] ?? ''))) . ' | 3. WAITING WO BLANK)</h3>';
            echo '<table border="1"><tr><th>Sales Leader</th><th>Total WO Today</th><th>SA (Active)</th><th>On Install</th><th>Reschedule</th><th>Waiting WO Today</th><th>Lainnya</th><th>WO Besok (&gt;= H+1)</th><th>Waiting WO (Blank)</th></tr>';
            foreach ($dlWoSum['leader_summary'] as $wr) {
                if (!empty($wr['is_grand_total']) && $dlScope !== 'Semua Leader') continue;
                if (empty($wr['is_grand_total']) && $dlScope !== 'Semua Leader' && $wr['leader'] !== $dlScope) continue;
                $sTot = (int)($wr['today_total'] ?? 0);
                $sSa  = (int)($wr['today_sa'] ?? 0);
                $sOn  = (int)($wr['today_on_installation'] ?? 0);
                $sRes = (int)($wr['today_reschedule'] ?? 0);
                $sWt  = (int)($wr['today_waiting_wo'] ?? 0);
                $sOth = (int)($wr['today_other'] ?? 0);
                $sBsk = (int)($wr['wo_besok'] ?? 0);
                $sWwo = (int)($wr['waiting_wo'] ?? 0);
                echo '<tr><td>' . htmlspecialchars((string)$wr['leader']) . "</td><td>{$sTot}</td><td>{$sSa}</td><td>{$sOn}</td><td>{$sRes}</td><td>{$sWt}</td><td>{$sOth}</td><td>{$sBsk}</td><td>{$sWwo}</td></tr>";
            }
        }
        $dlLdrKom = $appData['leader_komisi_rows'] ?? [];
        if (!empty($dlLdrKom) && $authU['role'] !== 'Agen') {
            echo '</table><br><h3>2A. REKAP KOMISI RESMI SALES LEADER (EXCL. PPN 11%)</h3><table border="1"><tr><th>Sales Leader</th><th>SA Tim</th><th>Rev. FP Tim (Excl. PPn)</th><th>Yearly Tim</th><th>Tier Leader</th><th>Insentif Leader</th><th>Total Komisi Agent</th><th>Total Komisi Tim</th></tr>';
            foreach ($dlLdrKom as $lk) {
                if (!empty($lk['is_total']) && $dlScope !== 'Semua Leader') continue;
                if (empty($lk['is_total']) && $dlScope !== 'Semua Leader' && $lk['leader'] !== $dlScope) continue;
                $lkRev = round((float)($lk['rev_fp_tim'] ?? 0), 0);
                echo '<tr><td>' . htmlspecialchars((string)$lk['leader']) . "</td><td>{$lk['sa_tim']}</td><td>{$lkRev}</td><td>{$lk['p_yr_tim']}</td><td>" . htmlspecialchars((string)$lk['tier_komisi']) . "</td><td>{$lk['insentif_leader']}</td><td>{$lk['total_komisi_agen']}</td><td>{$lk['total_komisi_tim']}</td></tr>";
            }
        }
        echo '</table><br><h3>2. DETAIL TARGET &amp; KOMISI AGENT</h3><table border="1"><tr><th>SALES LEADER</th><th>SALES NAME</th><th>MASA KERJA</th><th>LEVEL</th><th>TARGET ALL</th>';
        if ($dlAdmin) echo '<th>Reguler</th><th>Yearly</th>';
        echo '<th>SA</th><th>PAID</th><th>GAP SA</th><th>PERSENTASE</th><th>STATUS MTD</th><th>Harus Paid/Hr</th><th>Harus SA/Hr</th><th>RUNRATE</th><th>3 Monthly</th><th>Monthly</th><th>Semesterly</th><th>Yearly</th><th>Tier Komisi</th><th>Rev. FP (Excl. PPn)</th><th>Insentif FP</th><th>Ins. Yearly</th><th>Estimasi Komisi</th></tr>';
        foreach ($dlAgents as $r) {
            $rRev = round((float)($r['rev_fp'] ?? ($r['rev_netto'] ?? 0)), 0);
            $rTier = htmlspecialchars((string)($r['tier_komisi'] ?? 'Tier 0 (0%)'));
            $rInsFp = (float)($r['insentif_fp'] ?? 0);
            $rInsYr = (float)($r['insentif_yearly'] ?? 0);
            echo '<tr><td>' . htmlspecialchars($r['leader']) . '</td><td>' . htmlspecialchars($r['name']) . '</td><td>' . htmlspecialchars($r['masa_kerja']) . '</td><td>' . htmlspecialchars($r['level']) . "</td><td>{$r['target_all']}</td>";
            if ($dlAdmin) echo "<td>{$r['target_reguler']}</td><td>{$r['target_yearly']}</td>";
            echo "<td>{$r['sa_nov']}</td><td>{$r['paid_nov']}</td><td>{$r['gap_sa']}</td><td>{$r['persen']}%</td><td>" . htmlspecialchars($r['status_mtd']) . "</td><td>{$r['harus_paid_hr']}</td><td>{$r['harus_sa_hr']}</td><td>{$r['runrate_30']}</td><td>{$r['p_3m']}</td><td>{$r['p_m']}</td><td>{$r['p_sem']}</td><td>{$r['p_yr']}</td><td>{$rTier}</td><td>{$rRev}</td><td>{$rInsFp}</td><td>{$rInsYr}</td><td>{$r['est_komisi']}</td></tr>";
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
        $curRoleSw = $_SESSION['auth_user']['role'] ?? '';
        @session_write_close();
        if (!in_array($curRoleSw, ['Admin', 'Finance', 'Leader'], true)) {
            $actionStatus = '<div class="alert-err">🚫 Akses ditolak untuk mengubah tanggal laporan.</div>';
        } else {
            try {
                ensure_wo_summary_v2($appData, $poolActiveFile, $poolDefaultFile, $dataFile, $targetActiveFile, $targetDefaultFile);
                $hariCekIn = max(1, min(31, (int)($_POST['hari_harian_cek'] ?? 22)));
                if (!file_exists($targetActiveFile) && file_exists($targetDefaultFile)) {
                    @copy($targetDefaultFile, $targetActiveFile);
                }
                $poolNow = load_prospect_pool($poolActiveFile, $poolDefaultFile);
                $pCur = $appData['params'] ?? ['sheet' => "NOVEMBER'26", 'bulan_lalu' => 10, 'bulan_ini' => 11, 'tahun' => 2026, 'total_hari' => 30, 'hari_berjalan' => 22, 'rasio_paid' => 1.25];
                $hDlmBln = cal_days_in_month_aman((int)$pCur['bulan_ini'], (int)$pCur['tahun']);
                $tglTargetObj = new DateTimeImmutable(sprintf('%04d-%02d-%02d', (int)$pCur['tahun'], (int)$pCur['bulan_ini'], min((int)$pCur['hari_berjalan'], $hDlmBln)));
                $targetRows = baca_data_target($targetActiveFile, (string)$pCur['sheet'], $tglTargetObj);
                $dp = hitung_rekap_harian_blm_produktif($poolNow, $targetRows, (int)$pCur['bulan_ini'], (int)$pCur['tahun'], $hariCekIn);
                $appData['daily_prod_date_label'] = $dp['date_label'];
                $appData['daily_prod_day'] = $dp['day'];
                $appData['daily_prod_rows'] = $dp['rows'];
                $appData['params']['hari_harian'] = $dp['day'];
                $appData['tanggal_tersedia'] = daftar_hari_tersedia_bulan($poolNow, (int)$pCur['bulan_ini'], (int)$pCur['tahun'], $dp['day']);
                file_put_contents($dataFile, json_encode($appData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX);
                $actionStatus = '<div class="alert-ok">📅 Tanggal Tabel Harian &amp; Agent Blm Produktif diubah ke <b>' . htmlspecialchars($dp['date_label']) . '</b> langsung di server!</div>';
            } catch (Throwable $e) {
                $actionStatus = '<div class="alert-err">❌ Gagal mengganti tanggal harian: ' . htmlspecialchars($e->getMessage()) . '</div>';
            }
        }
    } elseif ($_POST['action'] === 'switch_wo_date' && !empty($_SESSION['auth_user'])) {
        // Ubah Tanggal Monitoring WO Today (WO Besok otomatis > Today) langsung di server
        $curRoleSw = $_SESSION['auth_user']['role'] ?? '';
        @session_write_close();
        if (!in_array($curRoleSw, ['Admin', 'Finance', 'Leader'], true)) {
            $actionStatus = '<div class="alert-err">🚫 Akses ditolak untuk mengubah tanggal Monitoring WO.</div>';
        } else {
            try {
                ensure_wo_summary_v2($appData, $poolActiveFile, $poolDefaultFile, $dataFile, $targetActiveFile, $targetDefaultFile);
                $hariWoCek = max(1, min(31, (int)($_POST['hari_wo_cek'] ?? ($appData['wo_summary']['day'] ?? ($appData['daily_prod_day'] ?? 22)))));
                $poolNow = load_prospect_pool($poolActiveFile, $poolDefaultFile);
                $pCur = $appData['params'] ?? ['bulan_ini' => 11, 'tahun' => 2026];
                $woRes = hitung_wo_laporan($poolNow, (int)($pCur['bulan_ini'] ?? 11), (int)($pCur['tahun'] ?? 2026), $hariWoCek);
                $appData['wo_summary'] = $woRes;
                $appData['params']['hari_wo'] = $woRes['day'];
                file_put_contents($dataFile, json_encode($appData, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX);
                $woTotR = (int)($woRes['wo_today_totals']['total'] ?? 0);
                $woSaR  = (int)($woRes['wo_today_totals']['sa'] ?? 0);
                $actionStatus = '<div class="alert-ok">🛠️ Monitoring WO diperbarui: <b>1. WO Today ' . htmlspecialchars($woRes['today_label']) . ': ' . $woTotR . ' (SA ' . $woSaR . ')</b> | <b>2. WO Besok (&gt;= ' . htmlspecialchars($woRes['besok_label']) . '): ' . (int)$woRes['wo_besok_total'] . '</b> | <b>3. Waiting WO (Blank): ' . (int)$woRes['waiting_wo_total'] . '</b>!</div>';
            } catch (Throwable $e) {
                $actionStatus = '<div class="alert-err">❌ Gagal memperbarui tanggal WO: ' . htmlspecialchars($e->getMessage()) . '</div>';
            }
        }
    } elseif ($_POST['action'] === 'upload_excel_data' && !empty($_SESSION['auth_user'])) {
        $curRole = $_SESSION['auth_user']['role'] ?? '';
        $curDisp = (string)($_SESSION['auth_user']['display_name'] ?? $curRole);
        $curUname = (string)($_SESSION['auth_user']['username'] ?? $curRole);
        @session_write_close();
        if (!in_array($curRole, ['Admin', 'Leader'], true)) {
            $actionStatus = '<div class="alert-err">🚫 Akses Ditolak: Hanya Super Admin dan Sales Leader yang diizinkan mengupdate data di server!</div>';
        } else {
            try {
                $sheetInput   = trim((string)($_POST['sheet_name'] ?? "NOVEMBER'26"));
                $bulanLaluIn  = max(1, min(12, (int)($_POST['bulan_lalu'] ?? 10)));
                $bulanIniIn   = max(1, min(12, (int)($_POST['bulan_ini'] ?? 11)));
                $tahunIn      = max(2020, min(2035, (int)($_POST['tahun'] ?? 2026)));
                $totalHariIn  = max(1, min(31, (int)($_POST['total_hari'] ?? 30)));
                $hariJalanIn  = max(1, min($totalHariIn, (int)($_POST['hari_berjalan'] ?? 22)));
                $hariHarianIn = max(1, min(31, (int)($_POST['hari_harian'] ?? $hariJalanIn)));
                $hariWoIn     = max(1, min(31, (int)($_POST['hari_wo'] ?? $hariHarianIn)));
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
                    'hari_wo'            => $hariWoIn,
                    'rasio_paid'         => $rasioPaidIn,
                    'simpan_pool_path'   => $poolActiveFile,
                ]);
                foreach ($tmpFilesToClean as $tf) @unlink($tf);

                $hasilBaru['bot_token_default'] = $appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs';
                $hasilBaru['docker_tunnel_url'] = $appData['docker_tunnel_url'] ?? '';
                $hasilBaru['sumber']['updated_at'] = date('Y-m-d H:i:s');
                $hasilBaru['sumber']['updated_by'] = $curDisp . ' (' . $curRole . ')';

                file_put_contents($dataFile, json_encode($hasilBaru, JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE), LOCK_EX);
                $appData = $hasilBaru;
                waf_log_event($auditLogFile, 'DATA-UPDATE', $curUname, 'Update server selesai: ' . ($hasilBaru['periode_label'] ?? ''));

                $jmlAgen = count($hasilBaru['agent_rows'] ?? []);
                $jmlBarisP = number_format((int)($hasilBaru['sumber']['total_baris_prospect'] ?? 0), 0, ',', '.');
                $infoUploadStr = !empty($uploadedProspects)
                    ? ('File Baru: ' . implode(', ', array_column($uploadedProspects, 'name')))
                    : 'Database Prospect Aktif Server';

                $actionStatus = '<div class="alert-ok">✅ <b>SEMUA DATA BERHASIL DI-UPDATE LANGSUNG KE SERVER (TANPA DOCKER)!</b><br>'
                    . '📊 Sheet Target: <b>' . htmlspecialchars($sheetInput) . '</b> (' . $jmlAgen . ' Agen) | '
                    . '📂 Total Prospect Unik: <b>' . $jmlBarisP . ' baris</b> (' . htmlspecialchars($infoUploadStr) . ') | '
                    . '🗓 Periode MTD: <b>' . htmlspecialchars($hasilBaru['periode_label']) . ' (' . $hasilBaru['target_persen_mtd'] . '%)</b> | '
                    . '📅 Cek Harian: <b>' . htmlspecialchars($hasilBaru['daily_prod_date_label'] ?? '') . '</b> | '
                    . '🛠️ WO Today: <b>' . (int)($hasilBaru['wo_summary']['wo_today_totals']['total'] ?? 0) . '</b> / Waiting: <b>' . (int)($hasilBaru['wo_summary']['waiting_wo_total'] ?? 0) . '</b> / Besok: <b>' . (int)($hasilBaru['wo_summary']['wo_besok_total'] ?? 0) . '</b></div>';
            } catch (Throwable $e) {
                $actionStatus = '<div class="alert-err">❌ <b>Gagal Memproses Data Excel:</b> ' . htmlspecialchars($e->getMessage()) . '</div>';
            }
        }
    } elseif ($_POST['action'] === 'reset_default_data' && !empty($_SESSION['auth_user'])) {
        $curRole = $_SESSION['auth_user']['role'] ?? '';
        $curUname = (string)($_SESSION['auth_user']['username'] ?? $curRole);
        @session_write_close();
        if (!in_array($curRole, ['Admin', 'Leader'], true)) {
            $actionStatus = '<div class="alert-err">🚫 Akses Ditolak!</div>';
        } else {
            if (file_exists($defaultDataFile)) @copy($defaultDataFile, $dataFile);
            if (file_exists($targetDefaultFile)) @copy($targetDefaultFile, $targetActiveFile);
            if (file_exists($poolDefaultFile)) @copy($poolDefaultFile, $poolActiveFile);
            $appData = load_json_safe($dataFile, []);
            waf_log_event($auditLogFile, 'DATA-RESET', $curUname, 'Reset ke dataset default server');
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
        $curRole = $_SESSION['auth_user']['role'] ?? '';
        if (!in_array($curRole, ['Admin', 'Finance', 'Leader'], true)) {
            $tgStatus = '<div class="alert-err">🚫 Akses Ditolak: Pengiriman laporan grup hanya tersedia untuk Admin, Finance, dan Sales Leader.</div>';
        } else {
            $defaultToken = $appData['bot_token_default'] ?? '9242894728:AAF2oYVZlpfcHEIFcC9PdoeFQA6KuwF-njs';
            $botToken = trim((string)($_POST['bot_token'] ?? ''));
            if ($botToken === '') $botToken = $defaultToken;
            $chatId = trim((string)($_POST['chat_id'] ?? ''));
            $scopeSend = (string)($_POST['scope_send'] ?? 'Yovi Arian');
            $sendMode = (string)($_POST['send_mode'] ?? 'auto');
            $imgMode  = (($_POST['img_mode'] ?? 'photo') === 'document') ? 'document' : 'photo';
            $incImg   = !empty($_POST['include_images']);
            $incTxt   = !empty($_POST['include_text']);
            $incWo    = !empty($_POST['include_wo']);
            $incWoCrd = !empty($_POST['include_wo_cards']);

            ensure_wo_summary_v2($appData, $poolActiveFile, $poolDefaultFile, $dataFile, $targetActiveFile, $targetDefaultFile);
            $agentRowsTg = $appData['agent_rows'] ?? [];
            $dailyRowsTg = $appData['daily_prod_rows'] ?? [];
            $dailyLblTg  = (string)($appData['daily_prod_date_label'] ?? '');
            $targetMtdTg = (int)($appData['target_persen_mtd'] ?? 50);
            $periodeLabelTg = (string)($appData['periode_label'] ?? '');
            $sisaHariTg = (int)($appData['sisa_hari'] ?? 15);
            $escTg = fn($s) => htmlspecialchars((string)$s, ENT_NOQUOTES, 'UTF-8');

            list($okChat, $msgChat) = waf_inspect_input($chatId, $auditLogFile);
            list($okTok, $msgTok)   = waf_inspect_input($botToken, $auditLogFile);
            if (!$okChat) {
                $tgStatus = '<div class="alert-err">' . htmlspecialchars($msgChat) . '</div>';
            } elseif (!$okTok) {
                $tgStatus = '<div class="alert-err">' . htmlspecialchars($msgTok) . '</div>';
            } elseif ($chatId === '') {
                $tgStatus = '<div class="alert-err">❌ Masukkan TELEGRAM_CHAT_ID terlebih dahulu (ketik <code>/id</code> di bot <b>@NoticeTelesalesbot</b>).</div>';
            } elseif (!$incImg && !$incTxt) {
                $tgStatus = '<div class="alert-err">⚠️ Pilih minimal satu format laporan (Gambar Presentasi .png atau Pesan Teks Detail).</div>';
            } else {
                $_SESSION['tg_last_bot_token'] = $botToken;
                @session_write_close();
                $messages = [];
                if ($incTxt) {
                    $blocks = [];
                    $hdrTg = "📊 <b>LAPORAN PERFORMA &amp; TARGET TELESALES ISP</b>\n"
                        . "🌐 Portal Resmi : <b>https://laporantelesalesoxygen.my.id</b>\n"
                        . "👨‍💼 Scope Leader : <b>" . $escTg($scopeSend) . "</b>\n"
                        . "🗓 Periode : <b>" . $escTg($periodeLabelTg) . " | Target MTD: {$targetMtdTg}%</b> (Sisa {$sisaHariTg} Hari)\n"
                        . "━━━━━━━━━━━━━━━━━━━━━━\n";

                    if (!empty($dailyRowsTg)) {
                        $blocks[] = "📅 <b>REKAP HARIAN (" . $escTg($dailyLblTg) . ") &amp; AGENT BLM PRODUKTIF</b>";
                        foreach ($dailyRowsTg as $dr) {
                            $isGt = !empty($dr['is_grand_total']);
                            if (!$isGt && $scopeSend !== 'Semua Leader' && $dr['leader'] !== $scopeSend) continue;
                            $dpGp = (int)($dr['gp'] ?? 0);
                            $lineDp = ($isGt ? "🏆 <b>" : "• <b>") . $escTg($dr['leader']) . "</b>: SO=<b>{$dr['so']}</b> GP=<b>{$dpGp}</b> PAID=<b>{$dr['paid']}</b> SA=<b>{$dr['sa']}</b> | Blm Prod: SO=<b>{$dr['blm_so']}</b> PAID=<b>{$dr['blm_paid']}</b> SA=<b>{$dr['blm_sa']}</b>";
                            if (!$isGt) {
                                $sPaid = implode(', ', $dr['agents_paid'] ?? []) ?: '-';
                                $sGp   = implode(', ', $dr['agents_gp'] ?? []) ?: '-';
                                $sTdk  = implode(', ', $dr['agents_tidak_paid'] ?? []) ?: 'Semua PAID';
                                $lineDp .= "\n   ✅ Sudah PAID (" . (int)($dr['sudah_paid_agents'] ?? 0) . "): " . $escTg($sPaid)
                                         . "\n   💳 Sudah GP (" . (int)($dr['sudah_gp_agents'] ?? 0) . "): " . $escTg($sGp)
                                         . "\n   ❌ Tidak PAID ({$dr['blm_paid']}): " . $escTg($sTdk);
                            }
                            $blocks[] = $lineDp;
                        }
                        $blocks[] = "━━━━━━━━━━━━━━━━━━━━━━\n";
                    }

                    $woSumTg = $appData['wo_summary'] ?? [];
                    if ($incWo && !empty($woSumTg['leader_summary'])) {
                        $besokRngTg = (string)($woSumTg['besok_range_label'] ?? ('>= ' . (string)($woSumTg['besok_label'] ?? '')));
                        $woLines = ["🛠️ <b>MONITORING WORK ORDER (1. Today " . $escTg((string)($woSumTg['today_label'] ?? '')) . " &amp; SA | 2. Besok " . $escTg($besokRngTg) . " | 3. Waiting WO)</b>"];
                        foreach ($woSumTg['leader_summary'] as $wr) {
                            $isGtW = !empty($wr['is_grand_total']);
                            if ($isGtW && $scopeSend !== 'Semua Leader') continue;
                            if (!$isGtW && $scopeSend !== 'Semua Leader' && ($wr['leader'] ?? '') !== $scopeSend) continue;
                            $tTot = (int)($wr['today_total'] ?? 0);
                            $tSa  = (int)($wr['today_sa'] ?? 0);
                            $tOn  = (int)($wr['today_on_installation'] ?? 0);
                            $tRes = (int)($wr['today_reschedule'] ?? 0);
                            $tWt  = (int)($wr['today_waiting_wo'] ?? 0);
                            $tOth = (int)($wr['today_other'] ?? 0);
                            $tBsk = (int)($wr['wo_besok'] ?? 0);
                            $tWwo = (int)($wr['waiting_wo'] ?? 0);
                            $woLines[] = ($isGtW ? "🏆 <b>" : "• <b>") . $escTg((string)($wr['leader'] ?? '')) . "</b>: WO Today=<b>{$tTot}</b> (<b>SA={$tSa}</b>, On Inst={$tOn}, Resched={$tRes}, Wait={$tWt}, Lain={$tOth}) | WO Besok=<b>{$tBsk}</b> | Waiting WO=<b>{$tWwo}</b>";
                        }
                        $blocks[] = implode("\n", $woLines) . "\n━━━━━━━━━━━━━━━━━━━━━━\n";
                    }

                    $no = 1;
                    $totT = 0; $totSa = 0; $totPaid = 0; $totKom = 0;
                    foreach ($agentRowsTg as $ag) {
                        if ($scopeSend !== 'Semua Leader' && $ag['leader'] !== $scopeSend) continue;
                        if (strtoupper($ag['name']) === 'VACANT') continue;
                        $totT += (int)$ag['target_all'];
                        $totSa += (int)$ag['sa_nov'];
                        $totPaid += (int)$ag['paid_nov'];
                        $totKom += (float)$ag['est_komisi'];
                        $komStr = 'Rp ' . number_format((float)$ag['est_komisi'], 0, ',', '.');
                        $tierAgTg = (string)($ag['tier_komisi'] ?? 'Tier 0 (0%)');
                        $blocks[] = "<b>{$no}. 👤 " . $escTg($ag['name']) . "</b> (" . $escTg($ag['level']) . ")\n"
                            . "├ 📌 Status MTD : <b>" . $escTg($ag['status_mtd']) . "</b> ({$ag['persen']}%)\n"
                            . "├ ✅ Realisasi : <b>{$ag['sa_nov']} SA</b> | <b>{$ag['paid_nov']} Paid</b> | Gap: {$ag['gap_sa']}\n"
                            . "├ ⚡ Wajib Harian : <b>{$ag['harus_paid_hr']} Paid/hr</b> &amp; <b>{$ag['harus_sa_hr']} SA/hr</b>\n"
                            . "└ 🎯 Target Total : <b>{$ag['target_all']} SA</b> | 💰 <b>{$komStr}</b> (" . $escTg($tierAgTg) . ")\n";
                        $no++;
                    }
                    $pctTim = $totT > 0 ? round(($totSa / $totT) * 100) : 0;
                    $totKomStr = 'Rp ' . number_format($totKom, 0, ',', '.');
                    $ldrKomExtra = '';
                    foreach (($appData['leader_komisi_rows'] ?? []) as $lkRow) {
                        if ($scopeSend === 'Semua Leader' && !empty($lkRow['is_total'])) {
                            $ldrKomExtra = ' | 👑 Ins. Leaders: Rp ' . number_format((float)$lkRow['insentif_leader'], 0, ',', '.');
                            break;
                        }
                        if ($scopeSend !== 'Semua Leader' && empty($lkRow['is_total']) && $lkRow['leader'] === $scopeSend) {
                            $ldrKomExtra = ' | 👑 Ins. Leader (' . (string)$lkRow['tier_komisi'] . '): Rp ' . number_format((float)$lkRow['insentif_leader'], 0, ',', '.');
                            break;
                        }
                    }
                    $blocks[] = "━━━━━━━━━━━━━━━━━━━━━━\n🏆 <b>TOTAL TIM: {$totSa} SA / Target {$totT} SA ({$pctTim}%) | Agent: {$totKomStr}{$ldrKomExtra}</b>";

                    $curMsg = $hdrTg;
                    foreach ($blocks as $b) {
                        $add = $b . "\n";
                        if (strlen($curMsg) + strlen($add) > 3500) {
                            $messages[] = trim($curMsg);
                            $curMsg = "📋 <b>Lanjutan Laporan (" . $escTg($scopeSend) . ")</b>\n━━━━━━━━━━━━━━━━━━━━━━\n" . $add;
                        } else {
                            $curMsg .= $add;
                        }
                    }
                    if (trim($curMsg) !== '') $messages[] = trim($curMsg);
                }

                // Teks dapat dikirim lewat Server PHP dulu bila bukan gambar & mode auto; jika perlu kirim gambar / server HTTP 0, browser mengirim rapi (Gambar -> Teks)
                $serverTextSent = false;
                $serverTextError = '';
                $needClientRunner = $incImg || ($sendMode === 'browser');

                if ($incTxt && !$needClientRunner) {
                    $serverTextSent = true;
                    foreach ($messages as $idxM => $mTxt) {
                        $resTg = send_telegram_server($botToken, $chatId, $mTxt);
                        if (!$resTg['ok']) {
                            $serverTextSent = false;
                            $serverTextError = "HTTP {$resTg['http_code']}: {$resTg['description']}";
                            if ($resTg['http_code'] === 0 && $idxM === 0) {
                                $needClientRunner = true;
                            }
                            break;
                        }
                    }
                }

                if ($serverTextSent && !$incImg) {
                    $tgStatus = '<div class="alert-ok">✅ Laporan teks berhasil dikirim ke Telegram Chat ID <b>' . htmlspecialchars($chatId) . '</b> (' . count($messages) . ' pesan, HTTP 200 OK)!</div>';
                } elseif ($needClientRunner) {
                    $visualData = $incImg ? build_tg_visual_payload($appData, $scopeSend, $incWo, $incWoCrd) : null;
                    $relayJson = json_encode([
                        'api_base'    => "https://api.telegram.org/bot{$botToken}",
                        'chat_id'     => $chatId,
                        'csrf_token'  => $csrfToken,
                        'img_mode'    => $imgMode,
                        'send_images' => $incImg,
                        'send_text'   => $incTxt && !$serverTextSent,
                        'messages'    => $incTxt ? $messages : [],
                        'visual_data' => $visualData,
                        'server_note' => $serverTextError,
                    ], JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE);

                    $tgStatus = '<div id="tg-relay-box" class="alert-ok" style="background:#eff6ff; color:#1e3a8a; border-color:#93c5fd;">'
                        . '<div style="display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap;">'
                        . '<span>⏳ <b>Menyiapkan &amp; Mengunggah Gambar Tabel (.png)' . ($incTxt ? ' + Pesan Teks' : '') . ' ke Telegram...</b></span>'
                        . '<button type="button" onclick="window.__TG_ABORT=true;" class="btn btn-red" style="padding:5px 12px; font-size:0.78rem;">⛔ Batalkan</button>'
                        . '</div>'
                        . '<div id="tg-relay-progress" style="margin-top:6px;">Memproses canvas presentasi resolusi tinggi...</div>'
                        . '</div>'
                        . '<script>window.__TG_SEND_CFG=' . $relayJson . ';</script>';
                } else {
                    $tgStatus = '<div class="alert-err">❌ Gagal mengirim ke Telegram (' . htmlspecialchars($serverTextError) . '). Pastikan Chat ID benar dan bot sudah di-<code>/start</code> atau masuk ke grup tujuan.</div>';
                }
            }
        }
    }
}

// Variabel tampilan terbaru dari $appData (auto-clean & auto-upgrade jika cache server masih versi lama)
if (!empty($_SESSION['auth_user'])) {
    ensure_wo_summary_v2($appData, $poolActiveFile, $poolDefaultFile, $dataFile, $targetActiveFile, $targetDefaultFile);
}
$mtdRows      = $appData['mtd_rows'] ?? [];
$agentRows    = $appData['agent_rows'] ?? [];
$leaderKomRows = $appData['leader_komisi_rows'] ?? [];
$dailyRows    = $appData['daily_prod_rows'] ?? [];
$dailyLbl     = (string)($appData['daily_prod_date_label'] ?? '22-Nov-26');
$dailyDay     = (int)($appData['daily_prod_day'] ?? 22);
$tglTersedia  = $appData['tanggal_tersedia'] ?? range(1, 22);
$woSummary    = $appData['wo_summary'] ?? [];
$woDay        = (int)($woSummary['day'] ?? $dailyDay);
$woAvailDays  = $woSummary['available_days'] ?? $tglTersedia;
$targetMtd    = (int)($appData['target_persen_mtd'] ?? 73);
$periodeLabel = $appData['periode_label'] ?? '22-Nov-2026';
$hariBerjalan = (int)($appData['hari_berjalan'] ?? 22);
$totalHari    = (int)($appData['total_hari'] ?? 30);
$sisaHari     = (int)($appData['sisa_hari'] ?? 8);
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
    'hari_berjalan' => 22,
    'hari_harian' => 22,
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
        .wo-tab-bar { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; align-items: center; }
        .wo-tab-btn {
            background: #e2e8f0; color: #0f172a; border: 1px solid #cbd5e1;
            padding: 8px 14px; border-radius: 8px; font-weight: 700; cursor: pointer; font-size: 0.84rem;
            transition: background 0.15s, color 0.15s;
        }
        .wo-tab-btn:hover { background: #cbd5e1; }
        .wo-tab-btn.active { background: #002060; color: #fff; border-color: #002060; }
        .wo-panel { display: none; }
        .wo-panel.active { display: block; }
        .wo-panel table thead th { position: sticky; top: 0; z-index: 2; }
        .wo-panel tbody tr:hover td { background: #f8fafc; }
        tr.row-wo-ltotal td { background: #dbeafe !important; font-weight: 700; color: #0f172a; }
        tr.row-wo-gtotal td { background: #fef3c7 !important; font-weight: 800; color: #0f172a; border-top: 2px solid #0f172a; }
        .wo-img-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 14px; margin-top: 12px; }
        .wo-card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(290px, 1fr)); gap: 12px; margin-top: 12px; }
        .wo-img-card {
            background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 10px;
            padding: 12px; display: flex; flex-direction: column; gap: 8px;
        }
        .wo-img-card img { max-width: 100%; height: auto; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; }
        .wo-toolbar {
            display: flex; flex-wrap: wrap; gap: 10px; align-items: end;
            background: #f1f5f9; border: 1px solid #cbd5e1; padding: 12px 14px; border-radius: 10px; margin: 10px 0;
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
    $filteredLeaderKomisi = array_values(array_filter($leaderKomRows, function ($lr) use ($selectedScope) {
        if (!empty($lr['is_total'])) return $selectedScope === 'Semua Leader';
        return $selectedScope === 'Semua Leader' || $lr['leader'] === $selectedScope;
    }));
    $sumInsLeaderScope = 0.0;
    foreach ($filteredLeaderKomisi as $lr) {
        if (empty($lr['is_total'])) $sumInsLeaderScope += (float)($lr['insentif_leader'] ?? 0);
    }

    $sumTargetAll = 0; $sumSaNov = 0; $sumPaidNov = 0; $sumKomisi = 0; $sumRevNetto = 0; $kurangCount = 0;
    foreach ($filteredAgents as $r) {
        $sumTargetAll += $r['target_all'];
        $sumSaNov += $r['sa_nov'];
        $sumPaidNov += $r['paid_nov'];
        $sumKomisi += $r['est_komisi'];
        $sumRevNetto += (float)($r['rev_fp'] ?? $r['rev_netto']);
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
                        <label style="font-size:0.81rem;"><b>Tanggal WO Today (Besok H+1):</b></label>
                        <input type="number" name="hari_wo" min="1" max="31" value="<?= (int)($paramsCur['hari_wo'] ?? $woDay) ?>" required>
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
                    <button type="submit" class="btn btn-green" style="padding:12px 24px;" onclick="this.textContent='⏳ Memproses Upload ke Server...';">
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
                💰 Estimasi Komisi (<?= htmlspecialchars((string)($ag['tier_komisi'] ?? 'Tier 0 (0%)')) ?>): <b><?= rp($ag['est_komisi']) ?></b>
                (FP: <?= rp($ag['insentif_fp'] ?? 0) ?> + Yearly: <?= rp($ag['insentif_yearly'] ?? 0) ?>)
            </p>
            <?php
            $agWoMine = null;
            $agKeyTarget = normalisasi_nama_agen($ag['name'] ?? '');
            foreach (($woSummary['agent_summary'] ?? []) as $awr) {
                if (normalisasi_nama_agen($awr['salesname'] ?? '') === $agKeyTarget) {
                    $agWoMine = $awr;
                    break;
                }
            }
            if ($agWoMine): ?>
                <div style="margin-top:10px; padding-top:10px; border-top:1px solid rgba(255,255,255,0.2); display:flex; flex-wrap:wrap; justify-content:space-between; align-items:center; gap:10px;">
                    <span style="font-size:0.88rem; color:#fde047;">
                        🛠️ <b>WO Pribadi Anda:</b>
                        1. WO Today (<?= htmlspecialchars((string)($woSummary['today_label'] ?? '')) ?>): <b><?= (int)($agWoMine['today_total'] ?? 0) ?></b>
                        (<b>SA <?= (int)($agWoMine['today_sa'] ?? 0) ?></b> | On Install <?= (int)($agWoMine['today_on_installation'] ?? 0) ?> | Resched <?= (int)($agWoMine['today_reschedule'] ?? 0) ?> | Wait <?= (int)($agWoMine['today_waiting_wo'] ?? 0) ?>) |
                        2. WO Besok (<?= htmlspecialchars((string)($woSummary['besok_range_label'] ?? ($woSummary['besok_label'] ?? ''))) ?>): <b><?= (int)($agWoMine['wo_besok'] ?? 0) ?></b> |
                        3. Waiting WO (Blank): <b><?= (int)($agWoMine['waiting_wo'] ?? 0) ?></b>
                    </span>
                    <button type="button" onclick="window.renderPersonalWoCard()" class="btn btn-amber" style="padding:6px 14px; font-size:0.82rem;">🖼️ Lihat &amp; Download Foto WO Saya (.png)</button>
                </div>
                <div id="agen-wo-card-box" style="display:none; margin-top:10px;"></div>
            <?php endif; ?>
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
            <div class="metric-label">💰 Total Estimasi Komisi Agent</div>
            <div class="metric-val"><?= rp($sumKomisi) ?></div>
            <div class="metric-sub">Rev. FP (Excl. PPn 11%): <?= rp($sumRevNetto) ?><?= $role !== 'Agen' ? ' | Ins. Leader: ' . rp($sumInsLeaderScope) : '' ?></div>
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
                            <th colspan="4" class="navy-hdr"><?= htmlspecialchars($dailyLbl) ?></th>
                            <th colspan="3" class="red-hdr">Jumlah Agent Blm Produktif</th>
                        </tr>
                        <tr>
                            <th class="navy-hdr">SO</th>
                            <th class="navy-hdr" style="color:#fde68a;">GP</th>
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
                            $gpCnt = (int)($dr['gp'] ?? 0);
                        ?>
                            <tr class="<?= $isGt ? 'row-grand' : '' ?>">
                                <td class="left"><?= htmlspecialchars($dr['leader']) ?></td>
                                <td><?= number_format((int)$dr['so'], 0, ',', '.') ?></td>
                                <td style="color:#92400e; font-weight:700;"><?= number_format($gpCnt, 0, ',', '.') ?></td>
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

            <div style="margin-top:12px; background:#f8fafc; padding:12px 14px; border-radius:10px; border:1px solid #cbd5e1;">
                <div style="font-weight:800; font-size:0.88rem; color:#0f172a; margin-bottom:8px;">
                    👥 Rincian Per Agent pada <?= htmlspecialchars($dailyLbl) ?> (Siapa Sudah PAID, Sudah GP &amp; Tidak PAID)
                </div>
                <div style="font-size:0.8rem; line-height:1.55; margin-bottom:10px;">
                    <?php
                    $allDailyAgDetails = [];
                    foreach ($dailyRows as $dr):
                        if (!empty($dr['is_grand_total'])) continue;
                        if ($selectedScope !== 'Semua Leader' && $dr['leader'] !== $selectedScope) continue;
                        foreach (($dr['agent_details'] ?? []) as $adItem) {
                            $allDailyAgDetails[] = $adItem;
                        }
                    ?>
                        <div style="margin-bottom:8px; padding:8px 10px; background:#ffffff; border-radius:8px; border:1px solid #e2e8f0;">
                            <b><?= htmlspecialchars($dr['leader']) ?></b> (<?= (int)$dr['total_agents'] ?> slot tim | SO: <?= (int)$dr['so'] ?>, GP: <?= (int)($dr['gp'] ?? 0) ?>, PAID: <?= (int)$dr['paid'] ?>, SA: <?= (int)$dr['sa'] ?>)<br>
                            <span style="color:#166534;">✅ <b>Sudah PAID (<?= (int)($dr['sudah_paid_agents'] ?? 0) ?>)</b></span>: <?= htmlspecialchars(implode(', ', $dr['agents_paid'] ?? []) ?: '-') ?><br>
                            <span style="color:#b45309;">💳 <b>Sudah GP (<?= (int)($dr['sudah_gp_agents'] ?? 0) ?>)</b></span>: <?= htmlspecialchars(implode(', ', $dr['agents_gp'] ?? []) ?: '-') ?><br>
                            <span style="color:#991b1b;">❌ <b>Tidak PAID (<?= (int)$dr['blm_paid'] ?>)</b></span>: <?= htmlspecialchars(implode(', ', $dr['agents_tidak_paid'] ?? []) ?: 'Semua PAID') ?><br>
                            <span style="color:#475569; font-size:0.76rem;">• <b>0 SO (<?= (int)$dr['blm_so'] ?>)</b>: <?= htmlspecialchars(implode(', ', $dr['agents_blm_so'] ?? []) ?: 'Semua Produktif') ?> | <b>0 SA (<?= (int)$dr['blm_sa'] ?>)</b>: <?= htmlspecialchars(implode(', ', $dr['agents_blm_sa'] ?? []) ?: 'Semua Produktif') ?></span>
                        </div>
                    <?php endforeach; ?>
                </div>

                <?php if (!empty($allDailyAgDetails)): ?>
                <div style="display:flex; gap:6px; flex-wrap:wrap; margin-bottom:8px;" id="dpAgentFilterBar">
                    <button type="button" class="btn" style="padding:5px 10px; font-size:0.76rem; background:#0f172a; color:#fff;" onclick="filterDailyAgents('all', this)">Semua Agent (<?= count($allDailyAgDetails) ?>)</button>
                    <button type="button" class="btn" style="padding:5px 10px; font-size:0.76rem; background:#dcfce7; color:#166534;" onclick="filterDailyAgents('paid', this)">✅ Sudah PAID</button>
                    <button type="button" class="btn" style="padding:5px 10px; font-size:0.76rem; background:#fef3c7; color:#92400e;" onclick="filterDailyAgents('gp', this)">💳 Sudah GP</button>
                    <button type="button" class="btn" style="padding:5px 10px; font-size:0.76rem; background:#fee2e2; color:#991b1b;" onclick="filterDailyAgents('tidak_paid', this)">❌ Tidak PAID</button>
                </div>
                <div class="table-wrap" style="max-height:360px; overflow-y:auto;">
                    <table id="tblDailyAgentDetail">
                        <thead>
                            <tr>
                                <th>Sales Leader</th>
                                <th>Salesname</th>
                                <th>SO</th>
                                <th>GP</th>
                                <th>PAID</th>
                                <th>Blm Paid (SO)</th>
                                <th>SA</th>
                                <th>Status Harian (<?= htmlspecialchars($dailyLbl) ?>)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($allDailyAgDetails as $ad):
                                $rowStCls = ((int)$ad['paid'] > 0) ? 'status-aman' : (((int)$ad['gp'] > 0 || (int)$ad['tidak_paid_so'] > 0) ? 'badge' : 'status-kurang');
                                $rowBgSty = !empty($ad['is_vacant']) ? ' class="row-vacant"' : '';
                            ?>
                            <tr<?= $rowBgSty ?> data-paid="<?= (int)$ad['paid'] ?>" data-gp="<?= (int)$ad['gp'] ?>">
                                <td class="left"><?= htmlspecialchars((string)$ad['leader']) ?></td>
                                <td class="left"><b><?= htmlspecialchars((string)$ad['name']) ?></b></td>
                                <td><?= (int)$ad['so'] ?></td>
                                <td style="color:#92400e; font-weight:700;"><?= (int)$ad['gp'] ?></td>
                                <td style="color:#166534; font-weight:700;"><?= (int)$ad['paid'] ?></td>
                                <td style="color:#991b1b;"><?= (int)$ad['tidak_paid_so'] ?></td>
                                <td><?= (int)$ad['sa'] ?></td>
                                <td class="left"><span class="<?= $rowStCls ?>" style="padding:2px 7px; border-radius:99px; font-size:0.74rem; <?= ($rowStCls === 'badge' ? 'background:#fef3c7;color:#92400e;font-weight:700;' : '') ?>"><?= htmlspecialchars((string)$ad['status_harian']) ?></span></td>
                            </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>
                <script>
                function filterDailyAgents(mode, btnEl) {
                    var tbl = document.getElementById('tblDailyAgentDetail');
                    if (!tbl) return;
                    var rows = tbl.querySelectorAll('tbody tr');
                    for (var i = 0; i < rows.length; i++) {
                        var tr = rows[i];
                        var p = parseInt(tr.getAttribute('data-paid') || '0', 10);
                        var g = parseInt(tr.getAttribute('data-gp') || '0', 10);
                        var show = true;
                        if (mode === 'paid') show = p > 0;
                        else if (mode === 'gp') show = g > 0;
                        else if (mode === 'tidak_paid') show = p === 0;
                        tr.style.display = show ? '' : 'none';
                    }
                }
                </script>
                <?php endif; ?>
            </div>
        </div>
        <?php endif; ?>
    </div>

    <?php if ($role !== 'Agen'):
        $woTodayCols    = $woSummary['wo_today_columns'] ?? [];
        $woTodayRows    = $woSummary['wo_today_rows'] ?? [];
        $woWaitingRows  = $woSummary['waiting_wo_rows'] ?? [];
        $woBesokRows    = $woSummary['wo_besok_rows'] ?? [];
        $woSumRows      = $woSummary['leader_summary'] ?? [];
        $woTodayLbl     = (string)($woSummary['today_label'] ?? $dailyLbl);
        $woBesokLbl     = (string)($woSummary['besok_label'] ?? '');
        $woBesokRngLbl  = (string)($woSummary['besok_range_label'] ?? ('>= ' . $woBesokLbl));
        $woBesokH1Tot   = (int)($woSummary['wo_besok_h1_total'] ?? 0);
        $woBesokLaterTot = (int)($woSummary['wo_besok_later_total'] ?? 0);
        $woWaitBrk      = $woSummary['waiting_wo_breakdown'] ?? [];

        // Hitung total mengikuti filter scope jika Leader / filter Admin tertentu dipilih
        $filtWoScope = function ($r) use ($selectedScope) {
            $rt = $r['row_type'] ?? '';
            $isGt = ($rt === 'grand_total') || !empty($r['is_grand_total']) || strcasecmp((string)($r['leader'] ?? ''), 'Grand Total') === 0;
            if ($isGt) return $selectedScope === 'Semua Leader';
            return $selectedScope === 'Semua Leader' || ($r['leader'] ?? '') === $selectedScope;
        };
        $dispTodayTot = 0; $dispTodaySa = 0; $dispOnI = 0; $dispResch = 0;
        $dispWaitToday = 0; $dispOther = 0; $dispBesokTot = 0; $dispWaitTot = 0;
        foreach ($woSumRows as $wsr) {
            if (!empty($wsr['is_grand_total'])) continue;
            if ($selectedScope !== 'Semua Leader' && ($wsr['leader'] ?? '') !== $selectedScope) continue;
            $dispTodayTot  += (int)($wsr['today_total'] ?? 0);
            $dispTodaySa   += (int)($wsr['today_sa'] ?? 0);
            $dispOnI       += (int)($wsr['today_on_installation'] ?? 0);
            $dispResch     += (int)($wsr['today_reschedule'] ?? 0);
            $dispWaitToday += (int)($wsr['today_waiting_wo'] ?? 0);
            $dispOther     += (int)($wsr['today_other'] ?? 0);
            $dispBesokTot  += (int)($wsr['wo_besok'] ?? 0);
            $dispWaitTot   += (int)($wsr['waiting_wo'] ?? 0);
        }
        $dispStCounts = [];
        foreach ($woTodayRows as $trSt) {
            if (($trSt['row_type'] ?? '') !== 'agent') continue;
            if ($selectedScope !== 'Semua Leader' && ($trSt['leader'] ?? '') !== $selectedScope) continue;
            foreach (($trSt['statuses'] ?? []) as $stK => $stV) {
                $dispStCounts[$stK] = ($dispStCounts[$stK] ?? 0) + (int)$stV;
            }
        }
        $todaySubParts = [];
        foreach ($woTodayCols as $cnSub) {
            $cntSub = (int)($dispStCounts[$cnSub] ?? 0);
            if ($cntSub > 0) {
                $lblSub = strcasecmp($cnSub, 'Active') === 0 ? 'SA (Active)' : $cnSub;
                $todaySubParts[] = htmlspecialchars($lblSub) . ': <b>' . $cntSub . '</b>';
            }
        }
        $saPctToday = $dispTodayTot > 0 ? round(($dispTodaySa / $dispTodayTot) * 100) : 0;
        $waitBrkParts = [];
        if ($selectedScope === 'Semua Leader') {
            foreach ($woWaitBrk as $wbK => $wbV) {
                if ((int)$wbV > 0) $waitBrkParts[] = htmlspecialchars((string)$wbK) . ': ' . (int)$wbV;
            }
        }
    ?>
    <!-- DASHBOARD 1C: MONITORING WORK ORDER (1. WO TODAY & SA | 2. WO BESOK | 3. WAITING WO) -->
    <div class="card">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px; margin-bottom:10px;">
            <div>
                <h3 style="margin:0;">🛠️ 1C. MONITORING WORK ORDER — 1. WO TODAY (<?= htmlspecialchars($woTodayLbl) ?>) | 2. WO BESOK | 3. WAITING WO</h3>
                <div style="font-size:0.82rem; color:#475569; margin-top:2px;">Pivot <b>Count of Customer Name</b> per Sales Leader &amp; Salesname dari kolom <code>Instalasi Date</code> dan <code>Status</code></div>
            </div>
            <form method="post" style="margin:0; display:flex; gap:6px; align-items:center;">
                <input type="hidden" name="action" value="switch_wo_date">
                <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
                <select name="hari_wo_cek" onchange="this.form.submit()" style="margin:0; width:auto; padding:6px 10px; font-size:0.84rem;">
                    <?php foreach ($woAvailDays as $wTg): ?>
                        <option value="<?= (int)$wTg ?>" <?= (int)$wTg === $woDay ? 'selected' : '' ?>>
                            WO Today: Tgl <?= (int)$wTg ?> <?= htmlspecialchars($lblBlnIni) ?>
                        </option>
                    <?php endforeach; ?>
                </select>
                <button type="submit" class="btn" style="padding:7px 12px; font-size:0.8rem;">🔄 Hitung WO</button>
            </form>
        </div>

        <?php if (empty($woSummary)): ?>
            <div class="alert-err" style="background:#fffbeb; color:#92400e; border-color:#fcd34d;">
                ℹ️ Data <b>WO TODAY / WO BESOK / WAITING WO</b> belum tersimpan di cache lama. Klik tombol <b>🔄 Hitung WO</b> di kanan atas atau upload ulang file <code>list_prospect</code> terbaru agar kolom <code>Instalasi Date</code> &amp; <code>Status</code> terhitung otomatis!
            </div>
        <?php else: ?>
            <div class="grid-3" style="margin-bottom:12px;">
                <div class="metric-box" style="border-left-color:#1d4ed8;">
                    <div class="metric-label">1️⃣ WO TODAY (<?= htmlspecialchars($woTodayLbl) ?>)</div>
                    <div class="metric-val">
                        <?= number_format($dispTodayTot, 0, ',', '.') ?> Customer
                        <span style="font-size:1rem; background:#dcfce7; color:#166534; padding:2px 9px; border-radius:999px; margin-left:4px; vertical-align:middle;">SA: <?= number_format($dispTodaySa, 0, ',', '.') ?> (<?= $saPctToday ?>%)</span>
                    </div>
                    <div class="metric-sub" style="color:#1e40af;"><?= $todaySubParts ? implode(' | ', $todaySubParts) : 'Belum ada data status' ?></div>
                </div>
                <div class="metric-box" style="border-left-color:#059669;">
                    <div class="metric-label">2️⃣ WO BESOK (<?= htmlspecialchars($woBesokRngLbl) ?>)</div>
                    <div class="metric-val"><?= number_format($dispBesokTot, 0, ',', '.') ?> Customer</div>
                    <div class="metric-sub" style="color:#065f46;">
                        Instalasi Date &gt; <?= htmlspecialchars($woTodayLbl) ?> (Status = ALL)
                        <?php if ($selectedScope === 'Semua Leader'): ?>
                            • H+1 (<?= htmlspecialchars($woBesokLbl) ?>): <b><?= $woBesokH1Tot ?></b> | Lusa+: <b><?= $woBesokLaterTot ?></b>
                        <?php endif; ?>
                    </div>
                </div>
                <div class="metric-box" style="border-left-color:#d97706;">
                    <div class="metric-label">3️⃣ WAITING WO (Instalasi Blank)</div>
                    <div class="metric-val"><?= number_format($dispWaitTot, 0, ',', '.') ?> Customer</div>
                    <div class="metric-sub" style="color:#b45309;">
                        <?= $waitBrkParts ? implode(' | ', $waitBrkParts) : 'Instalasi Date = (blank) | Back To Sales, READY, Reschedule, Waiting WO' ?>
                    </div>
                </div>
            </div>

            <div class="wo-tab-bar">
                <button type="button" class="wo-tab-btn active" onclick="window.switchWoTab('wo-tab-sum', this)">📊 Ringkasan Per Leader</button>
                <button type="button" class="wo-tab-btn" onclick="window.switchWoTab('wo-tab-today', this)">1️⃣ WO TODAY (<?= $dispTodayTot ?> | SA <?= $dispTodaySa ?>)</button>
                <button type="button" class="wo-tab-btn" onclick="window.switchWoTab('wo-tab-besok', this)">2️⃣ WO BESOK (<?= $dispBesokTot ?>)</button>
                <button type="button" class="wo-tab-btn" onclick="window.switchWoTab('wo-tab-wait', this)">3️⃣ WAITING WO (<?= $dispWaitTot ?>)</button>
                <button type="button" class="wo-tab-btn" id="wo-btn-gal" onclick="window.woOpenGalleryTab(this)">🖼️ Foto PNG (Ringkasan &amp; Masing-Masing Agent)</button>
            </div>

            <div id="wo-tab-sum" class="wo-panel active table-wrap">
                <table>
                    <thead>
                        <tr>
                            <th rowspan="2" class="navy-hdr">Sales Leader</th>
                            <th colspan="6" class="navy-hdr">1. WO TODAY (<?= htmlspecialchars($woTodayLbl) ?>)</th>
                            <th colspan="2" class="red-hdr">2. Besok &amp; 3. Waiting WO</th>
                        </tr>
                        <tr>
                            <th class="navy-hdr">Total Today</th>
                            <th class="navy-hdr">SA (Active)</th>
                            <th class="navy-hdr">On Install</th>
                            <th class="navy-hdr">Reschedule</th>
                            <th class="navy-hdr">Waiting WO</th>
                            <th class="navy-hdr">Lainnya</th>
                            <th class="red-hdr">WO Besok (<?= htmlspecialchars($woBesokRngLbl) ?>)</th>
                            <th class="red-hdr">Waiting WO (Blank)</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($woSumRows as $wr): if (!$filtWoScope($wr)) continue; $isGtW = !empty($wr['is_grand_total']); ?>
                            <tr class="<?= $isGtW ? 'row-wo-gtotal' : '' ?>">
                                <td class="left"><?= htmlspecialchars((string)$wr['leader']) ?></td>
                                <td><b><?= (int)($wr['today_total'] ?? 0) ?></b></td>
                                <td style="background:#dcfce7; color:#166534;"><b><?= (int)($wr['today_sa'] ?? 0) ?></b></td>
                                <td><?= (int)($wr['today_on_installation'] ?? 0) ?></td>
                                <td><?= (int)($wr['today_reschedule'] ?? 0) ?></td>
                                <td><?= (int)($wr['today_waiting_wo'] ?? 0) ?></td>
                                <td><?= (int)($wr['today_other'] ?? 0) ?></td>
                                <td><b><?= (int)($wr['wo_besok'] ?? 0) ?></b></td>
                                <td><b><?= (int)($wr['waiting_wo'] ?? 0) ?></b></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <div id="wo-tab-today" class="wo-panel table-wrap" style="max-height:560px; overflow-y:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Sales Leader</th>
                            <th>Salesname</th>
                            <?php foreach ($woTodayCols as $colNm): ?>
                                <th><?= htmlspecialchars(strcasecmp($colNm, 'Active') === 0 ? 'Active (SA)' : $colNm) ?></th>
                            <?php endforeach; ?>
                            <th>Grand Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($woTodayRows as $r): if (!$filtWoScope($r)) continue; $rt = $r['row_type'] ?? 'agent'; $stMapR = $r['statuses'] ?? []; ?>
                            <tr class="<?= $rt === 'grand_total' ? 'row-wo-gtotal' : ($rt === 'leader_total' ? 'row-wo-ltotal' : '') ?>">
                                <td class="left"><?= $rt === 'agent' ? htmlspecialchars((string)$r['leader']) : '' ?></td>
                                <td class="left"><?= htmlspecialchars((string)$r['salesname']) ?></td>
                                <?php foreach ($woTodayCols as $colNm): $vCell = (int)($stMapR[$colNm] ?? 0); $isSaC = strcasecmp($colNm, 'Active') === 0; ?>
                                    <td style="<?= $isSaC ? 'background:#f0fdf4; color:#166534; font-weight:700;' : '' ?>"><?= ($vCell > 0 || $rt === 'grand_total') ? $vCell : '' ?></td>
                                <?php endforeach; ?>
                                <td><b><?= (int)($r['total'] ?? 0) ?></b></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <div id="wo-tab-besok" class="wo-panel table-wrap" style="max-height:560px; overflow-y:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Sales Leader</th>
                            <th>Salesname</th>
                            <th>Grand Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($woBesokRows as $r): if (!$filtWoScope($r)) continue; $rt = $r['row_type'] ?? 'agent'; ?>
                            <tr class="<?= $rt === 'grand_total' ? 'row-wo-gtotal' : ($rt === 'leader_total' ? 'row-wo-ltotal' : '') ?>">
                                <td class="left"><?= $rt === 'agent' ? htmlspecialchars((string)$r['leader']) : '' ?></td>
                                <td class="left"><?= htmlspecialchars((string)$r['salesname']) ?></td>
                                <td><b><?= (int)$r['total'] ?></b></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <div id="wo-tab-wait" class="wo-panel table-wrap" style="max-height:560px; overflow-y:auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Sales Leader</th>
                            <th>Salesname</th>
                            <th>Grand Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        <?php foreach ($woWaitingRows as $r): if (!$filtWoScope($r)) continue; $rt = $r['row_type'] ?? 'agent'; ?>
                            <tr class="<?= $rt === 'grand_total' ? 'row-wo-gtotal' : ($rt === 'leader_total' ? 'row-wo-ltotal' : '') ?>">
                                <td class="left"><?= $rt === 'agent' ? htmlspecialchars((string)$r['leader']) : '' ?></td>
                                <td class="left"><?= htmlspecialchars((string)$r['salesname']) ?></td>
                                <td><b><?= (int)$r['total'] ?></b></td>
                            </tr>
                        <?php endforeach; ?>
                    </tbody>
                </table>
            </div>

            <div id="wo-tab-gallery" class="wo-panel">
                <div class="wo-toolbar">
                    <div style="flex:1; min-width:220px;">
                        <b style="color:#002060;">🖼️ Galeri Foto PNG Monitoring Work Order</b>
                        <div style="font-size:0.79rem; color:#475569;">Tersedia foto tabel <b>Ringkasan Leader</b>, <b>Pivot Detail 1/2/3</b>, <b>Per Tim Leader</b>, serta <b>Kartu Foto Masing-Masing Agent</b> siap unduh (PNG / ZIP) &amp; kirim Telegram.</div>
                    </div>
                    <button type="button" onclick="window.woRenderTableGallery()" class="btn" style="padding:8px 14px; font-size:0.83rem;">🖼️ Render Foto Ringkasan &amp; Tim</button>
                    <button type="button" onclick="window.woDownloadZip('tables')" class="btn btn-green" style="padding:8px 14px; font-size:0.83rem;">📦 Download Paket Foto Ringkasan (.zip)</button>
                </div>
                <div id="wo-gal-tables"></div>

                <hr style="margin:18px 0; border:0; border-top:1px solid #cbd5e1;">
                <div class="wo-toolbar">
                    <div style="min-width:190px; flex:1;">
                        <label style="font-size:0.8rem;"><b>Filter Leader (Kartu Masing-Masing Agent):</b></label>
                        <select id="wo-card-ldr-filter" style="margin:2px 0 0 0;" onchange="window.woPopulateAgentSelect()">
                            <option value="ALL">🌎 Semua Leader dalam Scope</option>
                        </select>
                    </div>
                    <div style="min-width:210px; flex:1;">
                        <label style="font-size:0.8rem;"><b>Pilih Agent Spesifik:</b></label>
                        <select id="wo-card-ag-filter" style="margin:2px 0 0 0;">
                            <option value="ALL">👥 Semua Agent Terpilih</option>
                        </select>
                    </div>
                    <button type="button" onclick="window.woRenderAgentCards()" class="btn btn-amber" style="padding:9px 14px; font-size:0.83rem;">👤 Tampilkan Foto Masing-Masing Agent</button>
                    <button type="button" onclick="window.woDownloadZip('agents')" class="btn btn-green" style="padding:9px 14px; font-size:0.83rem;">📦 Download Semua Foto Agent (.zip)</button>
                </div>
                <div id="wo-gal-agents"></div>
            </div>
        <?php endif; ?>
    </div>
    <?php endif; ?>

    <?php if ($role !== 'Agen' && !empty($filteredLeaderKomisi)): ?>
    <!-- DASHBOARD 2A: REKAP KOMISI RESMI SALES LEADER -->
    <div class="card">
        <h3 style="margin-top:0;">🏆 2A. REKAP KOMISI RESMI SALES LEADER (EXCL. PPN 11% — <code>Hitung Insentif FP</code>)</h3>
        <p style="font-size:0.82rem; color:#475569; margin-top:-4px; margin-bottom:10px;">
            <b>Leader:</b> Min 140 SA Tim &amp; Rev FP &ge; Rp 35jt (Tier 1: 4% | Tier 2 &ge; 37,5jt: 5% | Tier 3 &ge; 45jt: 6% | Tier 4 &ge; 55jt: 8%).
            <b>Agent:</b> Min 15 SA &amp; Rev FP &ge; Rp 3,75jt (Tier 1: 25% | Tier 2 &ge; 4,5jt: 30% | Tier 3 &ge; 5,5jt: 35%) + Bonus Yearly Rp 200.000/subs.
        </p>
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Sales Leader</th>
                        <th>SA Tim</th>
                        <th>Rev. FP Tim (Excl. PPn)</th>
                        <th>Yearly Tim</th>
                        <th>Tier Leader</th>
                        <th>Insentif Leader</th>
                        <th>Total Komisi Agent</th>
                        <th>Total Komisi Tim</th>
                    </tr>
                </thead>
                <tbody>
                    <?php foreach ($filteredLeaderKomisi as $lk):
                        $isTotLk = !empty($lk['is_total']);
                    ?>
                    <tr class="<?= $isTotLk ? 'row-total' : '' ?>">
                        <td class="left"><b><?= htmlspecialchars((string)$lk['leader']) ?></b></td>
                        <td class="col-sa"><?= number_format((int)$lk['sa_tim'], 0, ',', '.') ?></td>
                        <td class="left"><?= rp($lk['rev_fp_tim']) ?></td>
                        <td><?= (int)$lk['p_yr_tim'] ?></td>
                        <td><span class="badge" style="<?= ((int)$lk['pct_insentif'] > 0) ? 'background:#dcfce7;color:#166534;font-weight:700;' : 'background:#f1f5f9;color:#475569;' ?>"><?= htmlspecialchars((string)$lk['tier_komisi']) ?></span></td>
                        <td class="left"><b><?= rp($lk['insentif_leader']) ?></b></td>
                        <td class="left"><?= rp($lk['total_komisi_agen']) ?></td>
                        <td class="left"><b><?= rp($lk['total_komisi_tim']) ?></b></td>
                    </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
    <?php endif; ?>

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
                        <th>Tier Komisi</th>
                        <th>Rev. FP (Excl. PPn)</th>
                        <th>Insentif FP</th>
                        <th>Ins. Yearly</th>
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
                        $subPaidHr = 0; $subSaHr = 0; $sub3m = 0; $subM = 0; $subSem = 0; $subYrB = 0;
                        $subRevFp = 0; $subInsFp = 0; $subInsYr = 0; $subKom = 0;
                        foreach ($rowsLdr as $r):
                            $isVacant = strtoupper($r['name']) === 'VACANT';
                            $rRevFp = (float)($r['rev_fp'] ?? $r['rev_netto']);
                            $rInsFp = (float)($r['insentif_fp'] ?? 0);
                            $rInsYr = (float)($r['insentif_yearly'] ?? 0);
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
                            $subRevFp += $rRevFp;
                            $subInsFp += $rInsFp;
                            $subInsYr += $rInsYr;
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
                            <td><?= htmlspecialchars((string)($r['tier_komisi'] ?? 'Tier 0 (0%)')) ?></td>
                            <td class="left"><?= rp($rRevFp) ?></td>
                            <td class="left"><?= rp($rInsFp) ?></td>
                            <td class="left"><?= rp($rInsYr) ?></td>
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
                            <td>-</td>
                            <td class="left"><?= rp($subRevFp) ?></td>
                            <td class="left"><?= rp($subInsFp) ?></td>
                            <td class="left"><?= rp($subInsYr) ?></td>
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
                        <th>HARUS PAID / HARI</th><th>HARUS SA / HARI</th><th>TIER KOMISI</th><th>EST. KOMISI</th>
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
                            <td><?= htmlspecialchars((string)($kr['tier_komisi'] ?? 'Tier 0 (0%)')) ?></td>
                            <td class="left"><?= rp($kr['est_komisi']) ?></td>
                        </tr>
                    <?php endforeach; ?>
                </tbody>
            </table>
        </div>
    </div>
    <?php endif; ?>

    <?php if (in_array($role, ['Admin', 'Finance', 'Leader'], true)): ?>
    <!-- DASHBOARD 3: KIRIM GAMBAR PRESENTASI & TEKS KE BOT TELEGRAM -->
    <div class="card">
        <h3 style="margin-top:0;">📲 3. KIRIM GAMBAR PRESENTASI &amp; TEKS LENGKAP KE BOT TELEGRAM (<code>@NoticeTelesalesbot</code>)</h3>
        <p style="font-size:0.83rem; color:#475569; margin-top:-6px; margin-bottom:14px;">
            Sekarang mendukung pengiriman <b>🖼️ Gambar Tabel Presentasi (.png)</b> (Tabel MTD SA, Rekap Harian Blm Produktif, Ringkasan + Detail WO Today / Waiting WO / Besok / Per Tim, &amp; Detail Target Total per Leader — tanpa bocor detail Reguler/Yearly) <b>+ 📝 Pesan Teks Detail</b> langsung dari website!
            Pastikan bot <b>@NoticeTelesalesbot</b> sudah di-<code>/start</code> atau sudah dimasukkan ke grup Telegram tujuan.
        </p>

        <form method="post">
            <input type="hidden" name="action" value="send_telegram">
            <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($csrfToken) ?>">
            <input type="hidden" name="scope_send" value="<?= htmlspecialchars($selectedScope) ?>">
            <input type="hidden" name="bot_token" value="<?= htmlspecialchars($defaultToken) ?>">

            <div class="grid-3" style="align-items:end;">
                <div>
                    <label style="font-size:0.82rem;"><b>TELEGRAM_CHAT_ID Tujuan (ketik <code>/id</code> di bot):</b></label>
                    <input type="text" name="chat_id" value="<?= htmlspecialchars((string)($_POST['chat_id'] ?? '')) ?>" placeholder="Contoh: -100123456789 atau Chat ID Pribadi" required>
                </div>
                <div>
                    <label style="font-size:0.82rem;"><b>Format Pengiriman Gambar PNG:</b></label>
                    <select name="img_mode">
                        <option value="photo" <?= (($_POST['img_mode'] ?? 'photo') === 'photo') ? 'selected' : '' ?>>🖼️ Foto (langsung tampil rapi di chat Telegram)</option>
                        <option value="document" <?= (($_POST['img_mode'] ?? '') === 'document') ? 'selected' : '' ?>>📎 File / Dokumen PNG (resolusi asli tajam di-zoom)</option>
                    </select>
                </div>
                <div>
                    <label style="font-size:0.82rem;"><b>Jalur Pengiriman:</b></label>
                    <select name="send_mode">
                        <option value="auto" selected>⚡ Otomatis (Upload Gambar + Teks Anti-Blokir)</option>
                        <option value="browser">🌐 Langsung via Browser Relay</option>
                    </select>
                </div>
            </div>

            <div style="display:flex; gap:18px; flex-wrap:wrap; align-items:center; margin:4px 0 14px 0;">
                <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.88rem; font-weight:700;">
                    <input type="checkbox" name="include_images" value="1" <?= ($_SERVER['REQUEST_METHOD'] !== 'POST' || ($_POST['action'] ?? '') !== 'send_telegram' || !empty($_POST['include_images'])) ? 'checked' : '' ?> style="width:auto; margin:0;">
                    🖼️ Sertakan Gambar Presentasi Tabel (.png)
                </label>
                <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.88rem; font-weight:700;">
                    <input type="checkbox" name="include_text" value="1" <?= ($_SERVER['REQUEST_METHOD'] !== 'POST' || ($_POST['action'] ?? '') !== 'send_telegram' || !empty($_POST['include_text'])) ? 'checked' : '' ?> style="width:auto; margin:0;">
                    📝 Sertakan Pesan Teks Detail
                </label>
                <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.88rem; font-weight:700;">
                    <input type="checkbox" name="include_wo" value="1" <?= ($_SERVER['REQUEST_METHOD'] !== 'POST' || ($_POST['action'] ?? '') !== 'send_telegram' || !empty($_POST['include_wo'])) ? 'checked' : '' ?> style="width:auto; margin:0;">
                    🛠️ Sertakan Ringkasan &amp; Foto WO (Summary, Pivot 1/2/3 &amp; Tim)
                </label>
                <label style="display:inline-flex; align-items:center; gap:6px; cursor:pointer; font-size:0.88rem; font-weight:700;">
                    <input type="checkbox" name="include_wo_cards" value="1" <?= !empty($_POST['include_wo_cards']) ? 'checked' : '' ?> style="width:auto; margin:0;">
                    👤 Lampirkan Juga Foto Kartu Masing-Masing Agent WO
                </label>
            </div>

            <div style="display:flex; gap:10px; flex-wrap:wrap;">
                <button type="button" onclick="window.tgPreviewGallery()" class="btn btn-amber">👁️ Pratinjau &amp; Download Semua Gambar (.png)</button>
                <button type="submit" class="btn" style="flex:1; min-width:260px;">🚀 Kirim Gambar + Teks (<?= htmlspecialchars($selectedScope) ?>) ke Telegram</button>
            </div>
        </form>

        <div id="tg-preview-gallery" style="display:none; margin-top:18px; padding-top:14px; border-top:1px solid #cbd5e1;"></div>
    </div>
    <?php endif; ?>

    <?php
        $onlyAgJson = ($role === 'Agen') ? (string)($authUser['agent_name'] ?? '') : '';
        $previewJsonSpec = json_encode(
            build_tg_visual_payload($appData, $selectedScope, true, false, $onlyAgJson),
            JSON_HEX_TAG | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_HEX_AMP | JSON_UNESCAPED_UNICODE | JSON_INVALID_UTF8_SUBSTITUTE
        );
    ?>
    <script>
    window.switchWoTab = function(panelId, btnEl) {
        document.querySelectorAll('.wo-panel').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.wo-tab-btn').forEach(b => b.classList.remove('active'));
        const tgt = document.getElementById(panelId);
        if (tgt) tgt.classList.add('active');
        if (btnEl) btnEl.classList.add('active');
    };
    (function(){
        const PREVIEW_DATA = <?= $previewJsonSpec ?>;
        const F_FACE = "'Segoe UI', Roboto, Arial, sans-serif";

        async function fetchWithTimeout(url, opts, ms) {
            const ctrl = (typeof AbortController !== 'undefined') ? new AbortController() : null;
            const tId = ctrl ? setTimeout(() => ctrl.abort(new Error('Koneksi timeout (' + Math.round(ms / 1000) + 's)')), ms) : null;
            try {
                const reqOpts = ctrl ? Object.assign({}, opts, { signal: ctrl.signal }) : opts;
                return await fetch(url, reqOpts);
            } finally {
                if (tId) clearTimeout(tId);
            }
        }

        function fmtInt(n) {
            const v = Math.round(Number(n) || 0);
            const sign = v < 0 ? '-' : '';
            return sign + Math.abs(v).toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        }
        function roundExcel(v) {
            const x = Number(v) || 0;
            return x >= 0 ? Math.floor(x + 0.5) : Math.ceil(x - 0.5);
        }

        function measureMulti(ctx, text, font) {
            ctx.font = font;
            const lines = String(text).split('\n');
            let m = 0;
            for (const ln of lines) m = Math.max(m, ctx.measureText(ln).width);
            return m;
        }

        function drawTextCell(ctx, box, text, font, color, align) {
            const [x0, y0, x1, y1] = box;
            const lines = String(text).split('\n');
            const sizeMatch = /\b(\d+)px\b/.exec(font);
            const px = sizeMatch ? Number(sizeMatch[1]) : 16;
            const lineH = px * 1.2;
            let y = (y0 + y1) / 2 - (lineH * lines.length) / 2 + lineH / 2;
            ctx.font = font;
            ctx.fillStyle = color;
            ctx.textBaseline = 'middle';
            for (const ln of lines) {
                if (align === 'l') {
                    ctx.textAlign = 'left';
                    ctx.fillText(ln, x0 + 12, y);
                } else if (align === 'r') {
                    ctx.textAlign = 'right';
                    ctx.fillText(ln, x1 - 12, y);
                } else {
                    ctx.textAlign = 'center';
                    ctx.fillText(ln, (x0 + x1) / 2, y);
                }
                y += lineH;
            }
        }

        function renderTablePng(spec) {
            const margin = 28;
            const padCell = 14;
            const rowH = 38;
            const fTitle = '800 26px ' + F_FACE;
            const fSub   = '400 16px ' + F_FACE;
            const fHead  = '700 15px ' + F_FACE;
            const fGroup = '700 15px ' + F_FACE;
            const fCell  = '400 16px ' + F_FACE;
            const fBold  = '700 16px ' + F_FACE;
            const fNote  = '400 14px ' + F_FACE;
            const fBan   = '800 16px ' + F_FACE;

            const tmpCanvas = document.createElement('canvas');
            const mCtx = tmpCanvas.getContext('2d');
            const nCol = spec.columns.length;
            const align = spec.align || Array(nCol).fill('c');
            const groups = spec.groupHeaders || [];
            const notes = spec.notes || [];

            let colW = [];
            for (let c = 0; c < nCol; c++) {
                let w = measureMulti(mCtx, spec.columns[c], fHead);
                for (const r of spec.rows) {
                    w = Math.max(w, measureMulti(mCtx, r[c], fBold));
                }
                colW.push(w + 2 * padCell);
            }
            for (const g of groups) {
                const need = measureMulti(mCtx, g.label, fGroup) + 2 * padCell;
                let have = 0;
                for (let c = g.start; c <= g.end; c++) have += colW[c];
                if (need > have) {
                    const add = (need - have) / (g.end - g.start + 1);
                    for (let c = g.start; c <= g.end; c++) colW[c] += add;
                }
            }

            let banW = 0, banLW = 0, banH = 0;
            if (spec.banner) {
                banLW = measureMulti(mCtx, spec.banner.left, fBan) + 36;
                const banRW = measureMulti(mCtx, spec.banner.right, fBan) + 36;
                banW = Math.max(banLW + banRW, measureMulti(mCtx, spec.banner.top, fBan) + 36);
                banH = 68;
            }

            const titleW = Math.max(measureMulti(mCtx, spec.title, fTitle), measureMulti(mCtx, spec.subtitle, fSub));
            let noteW = 0;
            for (const nt of notes) noteW = Math.max(noteW, measureMulti(mCtx, nt, fNote));
            const tableW = colW.reduce((a, b) => a + b, 0);
            const contentW = Math.max(tableW, titleW + (spec.banner ? banW + 40 : 0), noteW);
            if (contentW > tableW) {
                const ratio = contentW / tableW;
                colW = colW.map(w => w * ratio);
            }
            colW = colW.map(w => Math.ceil(w));
            const totalW = colW.reduce((a, b) => a + b, 0);

            const maxHeadLines = Math.max(...spec.columns.map(k => String(k).split('\n').length));
            const headH = Math.ceil(maxHeadLines * 18 + 20);
            const groupH = groups.length ? 34 : 0;
            const titleBlkH = Math.max(66, banH) + 20;
            const noteH = notes.length ? (notes.length * 22 + 16) : 0;

            const imgW = totalW + 2 * margin;
            const imgH = margin + 8 + titleBlkH + groupH + headH + spec.rows.length * rowH + noteH + margin;

            const canvas = document.createElement('canvas');
            const scale = (imgW * 1.5 + imgH * 1.5 <= 9000) ? 1.5 : 1.0;
            canvas.width = Math.round(imgW * scale);
            canvas.height = Math.round(imgH * scale);
            const ctx = canvas.getContext('2d');
            ctx.scale(scale, scale);

            ctx.fillStyle = '#ffffff';
            ctx.fillRect(0, 0, imgW, imgH);
            ctx.fillStyle = '#1f3864';
            ctx.fillRect(0, 0, imgW, 8);

            const y0 = margin + 8;
            ctx.fillStyle = '#0f172a';
            ctx.font = fTitle;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            ctx.fillText(spec.title, margin, y0);
            ctx.fillStyle = '#475569';
            ctx.font = fSub;
            ctx.fillText(spec.subtitle, margin, y0 + 36);

            if (spec.banner) {
                const bx1 = margin + totalW;
                const bx0 = bx1 - banW;
                const bxm = bx0 + banLW;
                ctx.fillStyle = '#6b1d36';
                ctx.fillRect(bx0, y0, banW, 32);
                ctx.strokeStyle = '#4a1525';
                ctx.strokeRect(bx0, y0, banW, 32);
                drawTextCell(ctx, [bx0, y0, bx1, y0 + 32], spec.banner.top, fBan, '#ffffff', 'c');

                ctx.fillStyle = '#58152b';
                ctx.fillRect(bx0, y0 + 32, banLW, 36);
                ctx.fillRect(bxm, y0 + 32, bx1 - bxm, 36);
                ctx.strokeStyle = '#993355';
                ctx.strokeRect(bx0, y0 + 32, banLW, 36);
                ctx.strokeRect(bxm, y0 + 32, bx1 - bxm, 36);
                drawTextCell(ctx, [bx0, y0 + 32, bxm, y0 + 68], spec.banner.left, fBan, '#ffffff', 'c');
                drawTextCell(ctx, [bxm, y0 + 32, bx1, y0 + 68], spec.banner.right, fBan, '#fde047', 'c');
            }

            const yTab = y0 + titleBlkH;
            const xs = [margin];
            for (const w of colW) xs.push(xs[xs.length - 1] + w);

            const groupedCols = new Set();
            const colHeadBg = {};
            for (const g of groups) {
                const bgG = g.bg || '#1f3864';
                for (let c = g.start; c <= g.end; c++) {
                    groupedCols.add(c);
                    colHeadBg[c] = bgG;
                }
                ctx.fillStyle = bgG;
                ctx.fillRect(xs[g.start], yTab, xs[g.end + 1] - xs[g.start], groupH);
                ctx.strokeStyle = '#5b6f99';
                ctx.strokeRect(xs[g.start], yTab, xs[g.end + 1] - xs[g.start], groupH);
                drawTextCell(ctx, [xs[g.start], yTab, xs[g.end + 1], yTab + groupH], g.label, fGroup, '#ffffff', 'c');
            }

            for (let c = 0; c < nCol; c++) {
                const bgH = colHeadBg[c] || spec.headBg || '#1f3864';
                const topY = groupedCols.has(c) ? (yTab + groupH) : yTab;
                const hH = groupedCols.has(c) ? headH : (groupH + headH);
                ctx.fillStyle = bgH;
                ctx.fillRect(xs[c], topY, xs[c + 1] - xs[c], hH);
                ctx.strokeStyle = '#5b6f99';
                ctx.strokeRect(xs[c], topY, xs[c + 1] - xs[c], hH);
                drawTextCell(ctx, [xs[c], topY, xs[c + 1], topY + hH], spec.columns[c], fHead, '#ffffff', 'c');
            }

            let y = yTab + groupH + headH;
            for (let i = 0; i < spec.rows.length; i++) {
                const row = spec.rows[i];
                const rb = (spec.rowStyles && spec.rowStyles[i]) || {};
                const baseBg = rb.bg || (i % 2 ? '#f5f7fb' : '#ffffff');
                for (let c = 0; c < nCol; c++) {
                    const cs = (spec.cellStyle ? spec.cellStyle(i, c, row[c]) : null) || {};
                    const bg = cs.bg || baseBg;
                    const fg = cs.fg || rb.fg || '#0f172a';
                    const isBold = (cs.bold !== undefined) ? cs.bold : !!rb.bold;
                    const al = cs.align || align[c];
                    ctx.fillStyle = bg;
                    ctx.fillRect(xs[c], y, xs[c + 1] - xs[c], rowH);
                    ctx.strokeStyle = '#a7b1c2';
                    ctx.strokeRect(xs[c], y, xs[c + 1] - xs[c], rowH);
                    drawTextCell(ctx, [xs[c], y, xs[c + 1], y + rowH], row[c], isBold ? fBold : fCell, fg, al);
                }
                y += rowH;
            }
            ctx.strokeStyle = '#1f3864';
            ctx.lineWidth = 2;
            ctx.strokeRect(margin, yTab, totalW, y - yTab);
            ctx.lineWidth = 1;

            let ny = y + 18;
            ctx.fillStyle = '#475569';
            ctx.font = fNote;
            ctx.textAlign = 'left';
            ctx.textBaseline = 'top';
            for (const nt of notes) {
                ctx.fillText(nt, margin, ny);
                ny += 22;
            }

            return new Promise(resolve => {
                canvas.toBlob(blob => {
                    resolve({ blob: blob, dataUrl: canvas.toDataURL('image/png') });
                }, 'image/png');
            });
        }

        async function renderAgentWoCardPng(ag, todayLbl, besokLbl) {
            const totI = Number(ag.today_total || 0), saI = Number(ag.today_sa || 0);
            const onI = Number(ag.today_on_installation || 0), resI = Number(ag.today_reschedule || 0);
            const wtI = Number(ag.today_waiting_wo || 0), othI = Number(ag.today_other || 0);
            const bskI = Number(ag.wo_besok || 0), wwoI = Number(ag.waiting_wo || 0);
            const imgC = await renderTablePng({
                title: `KARTU WO AGENT — ${String(ag.salesname).toUpperCase()}`,
                subtitle: `Sales Leader: ${ag.leader}  •  WO Today: ${todayLbl}  •  WO Besok: >= ${besokLbl}`,
                columns: ['SALESNAME', 'TOTAL TODAY', 'SA (ACTIVE)', 'ON INSTALL', 'RESCHED', 'WAIT WO', 'LAINNYA', `WO BESOK (>=${besokLbl})`, 'WAITING WO'],
                groupHeaders: [
                    { label: `1. WO TODAY (${todayLbl})`, start: 1, end: 6, bg: '#002060' },
                    { label: '2. BESOK & 3. WAITING WO', start: 7, end: 8, bg: '#065f46' },
                ],
                rows: [[
                    ag.salesname,
                    fmtInt(totI), fmtInt(saI), fmtInt(onI), fmtInt(resI), fmtInt(wtI), fmtInt(othI),
                    fmtInt(bskI), fmtInt(wwoI),
                ]],
                align: ['l', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
                rowStyles: [{ bg: '#ffffff', bold: true }],
                cellStyle: (_i, c) => {
                    if (c === 1) return { bg: '#dbeafe', fg: '#1e3a8a', bold: true };
                    if (c === 2) return { bg: '#bbf7d0', fg: '#14532d', bold: true };
                    if (c === 7) return { bg: '#dcfce7', fg: '#065f46', bold: true };
                    if (c === 8) return { bg: '#fef3c7', fg: '#92400e', bold: true };
                    return null;
                },
                notes: [`Kartu Monitoring WO Pribadi — ${ag.salesname} (${ag.leader})`],
            });
            const safeSn = String(ag.salesname).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '') || 'Agent';
            const escSn = String(ag.salesname).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            const escLd = String(ag.leader).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
            return {
                fileName: `01E_WO_Agent_${safeSn}.png`,
                caption: `👤 <b>Kartu WO — ${escSn}</b> (${escLd}) | Today: ${totI} (SA ${saI}) | Besok: ${bskI} | Waiting: ${wwoI}`,
                blob: imgC.blob,
                dataUrl: imgC.dataUrl,
            };
        }

        async function buildAllReportPngs(data) {
            const out = [];

            // 1. MTD SA
            if (data.mtd_rows && data.mtd_rows.length) {
                let totOct = 0, totNov = 0;
                const rows = [];
                const rowStyles = [];
                let idxTot = -1;
                for (const mr of data.mtd_rows) {
                    if (mr.is_total) {
                        totOct = mr.sa_oct;
                        totNov = mr.sa_nov;
                        idxTot = rows.length;
                        rowStyles.push({ bg: '#c9daf8', bold: true });
                    } else {
                        rowStyles.push(null);
                    }
                    rows.push([mr.leader, fmtInt(mr.sa_oct), fmtInt(mr.sa_nov), fmtInt(mr.gap_sa)]);
                }
                const acv = totOct > 0 ? roundExcel(((totNov - totOct) / totOct) * 100) : 0;
                const idxNote = rows.length;
                rows.push(['Note Acv SA', '', acv < 0 ? '↓' : '↑', acv + '%']);
                rowStyles.push({ bg: '#dbe5f1', bold: true });

                const imgMtd = await renderTablePng({
                    title: 'MTD SA — RINGKASAN PENCAPAIAN LEADER',
                    subtitle: `Perbandingan tanggal 1-${data.hari} ${data.bln_lalu} vs ${data.bln_ini} ${data.tahun} (${data.scope})`,
                    columns: ['SALES LEADER', `SA ${data.bln_lalu}\n1-${data.hari}`, `SA ${data.bln_ini}\n1-${data.hari}`, 'GAP SA'],
                    rows: rows,
                    align: ['l', 'c', 'c', 'c'],
                    rowStyles: rowStyles,
                    cellStyle: (i, c, txt) => {
                        if (c === 0 && (i === idxTot || i === idxNote)) return { align: 'c' };
                        if (c === 3) {
                            const v = parseInt(String(txt).replace(/\./g, '').replace('%', ''), 10);
                            if (!isNaN(v) && v < 0) return { bg: '#f4cccc', fg: '#990000', bold: true };
                            if (!isNaN(v) && v > 0) return { fg: '#15803d', bold: true };
                        }
                        return null;
                    },
                    notes: [`GAP SA = SA ${data.bln_ini} - SA ${data.bln_lalu}. Note Acv SA = kenaikan/penurunan terhadap bulan lalu.`],
                });
                out.push({
                    fileName: `01_MTD_SA_1-${data.hari}_${data.bln_ini}_${data.tahun}.png`,
                    caption: `📈 <b>MTD SA 1-${data.hari} ${data.bln_lalu} vs ${data.bln_ini} ${data.tahun}</b>`,
                    blob: imgMtd.blob,
                    dataUrl: imgMtd.dataUrl,
                });
            }

            // 1B. REKAP HARIAN & AGENT BELUM PRODUKTIF
            if (data.daily_rows && data.daily_rows.length) {
                const dRows = [];
                const dStyles = [];
                let idxGt = -1;
                for (const dr of data.daily_rows) {
                    if (dr.is_gt) {
                        idxGt = dRows.length;
                        dStyles.push({ bg: '#ffffff', bold: true });
                    } else {
                        dStyles.push(null);
                    }
                    dRows.push([dr.leader, fmtInt(dr.so), fmtInt(dr.gp || 0), fmtInt(dr.paid), fmtInt(dr.sa), fmtInt(dr.blm_so), fmtInt(dr.blm_paid), fmtInt(dr.blm_sa)]);
                }
                const imgDp = await renderTablePng({
                    title: `REKAP HARIAN (${data.daily_label}) & AGENT BELUM PRODUKTIF`,
                    subtitle: `SO / GP (Generate Payment) / PAID / SA tanggal ${data.daily_label} vs Jumlah Agent Aktif Belum Produktif`,
                    columns: ['Sales Leader', 'SO', 'GP', 'PAID', 'SA', 'SO', 'PAID', 'SA'],
                    groupHeaders: [
                        { label: data.daily_label, start: 1, end: 4, bg: '#002060' },
                        { label: 'Jumlah Agent Blm Produktif', start: 5, end: 7, bg: '#dc0000' },
                    ],
                    headBg: '#002060',
                    rows: dRows,
                    align: ['l', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
                    rowStyles: dStyles,
                    cellStyle: (i, c) => (i === idxGt && c >= 5) ? { bg: '#fce4d6', fg: '#9a3412', bold: true } : null,
                    notes: [`GP = Generate Payment belum Paid | Kolom Merah: Agen aktif non-Vacant dengan hasil 0 tepat pada ${data.daily_label}.`],
                });
                out.push({
                    fileName: `01B_Rekap_Harian_Blm_Produktif_${data.daily_label}.png`,
                    caption: `📊 <b>Rekap Harian (${data.daily_label}) &amp; Jumlah Agent Belum Produktif</b>`,
                    blob: imgDp.blob,
                    dataUrl: imgDp.dataUrl,
                });

                for (const dr of data.daily_rows) {
                    if (dr.is_gt || !Array.isArray(dr.agent_details) || !dr.agent_details.length) continue;
                    const agRows = [];
                    const agStyles = [];
                    let sumSo = 0, sumGp = 0, sumPaid = 0, sumUnp = 0, sumSa = 0, cPaid = 0, cGp = 0, cTdk = 0;
                    for (const ad of dr.agent_details) {
                        const isVac = !!ad.is_vacant;
                        sumSo += (ad.so || 0); sumGp += (ad.gp || 0); sumPaid += (ad.paid || 0); sumUnp += (ad.tidak_paid_so || 0); sumSa += (ad.sa || 0);
                        if (!isVac) {
                            if ((ad.paid || 0) > 0) cPaid++; else cTdk++;
                            if ((ad.gp || 0) > 0) cGp++;
                        }
                        agRows.push([ad.name, fmtInt(ad.so), fmtInt(ad.gp), fmtInt(ad.paid), fmtInt(ad.tidak_paid_so), fmtInt(ad.sa), ad.status_harian || '']);
                        agStyles.push(isVac ? { bg: '#ffff00', bold: true } : null);
                    }
                    const idxTotAg = agRows.length;
                    agRows.push([`TOTAL TIM (${dr.agent_details.length} slot)`, fmtInt(sumSo), fmtInt(sumGp), fmtInt(sumPaid), fmtInt(sumUnp), fmtInt(sumSa), `Paid: ${cPaid} | GP: ${cGp} | Tdk Paid: ${cTdk}`]);
                    agStyles.push({ bg: '#c9daf8', bold: true });
                    const imgAgDp = await renderTablePng({
                        title: `RINCIAN HARIAN PER AGENT — TIM ${String(dr.leader).toUpperCase()} (${data.daily_label})`,
                        subtitle: `Siapa Sudah PAID (${cPaid}), Sudah GP (${cGp}), & Tidak PAID (${cTdk})`,
                        columns: ['Salesname', 'SO', 'GP', 'PAID', 'Belum Paid\n(SO)', 'SA', 'Status Harian'],
                        rows: agRows,
                        align: ['l', 'c', 'c', 'c', 'c', 'c', 'l'],
                        rowStyles: agStyles,
                        cellStyle: (i, c, txt) => {
                            if (i === idxTotAg || c !== 6) return null;
                            if (String(txt).includes('Sudah PAID')) return { bg: '#d9ead3', fg: '#134f5c', bold: true };
                            if (String(txt).includes('Sudah GP') || String(txt).includes('Baru SO')) return { bg: '#fff2cc', fg: '#7f4f00', bold: true };
                            if (String(txt).includes('Tidak PAID')) return { bg: '#f4cccc', fg: '#990000', bold: true };
                            return null;
                        },
                        notes: ['Hijau = Sudah PAID | Kuning = Sudah GP / pending SO (belum PAID) | Merah = Tidak PAID (0 SO).'],
                    });
                    const safeD = String(dr.leader).replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '');
                    const escD = String(dr.leader).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    out.push({
                        fileName: `01B2_Rincian_Agent_Harian_${safeD}_${data.daily_label}.png`,
                        caption: `👥 <b>Rincian Harian Agent — Tim ${escD} (${data.daily_label})</b> | Paid: ${cPaid} | GP: ${cGp} | Tdk Paid: ${cTdk}`,
                        blob: imgAgDp.blob,
                        dataUrl: imgAgDp.dataUrl,
                    });
                }
            }

            // 1C. MONITORING WORK ORDER (RINGKASAN + PIVOT 1/2/3 + FOTO TIM PER LEADER + KARTU AGENT)
            async function renderWoPivotPng(ws, mode) {
                const isToday = mode === 'today';
                const isBesok = mode === 'besok';
                const src = isToday ? (ws.wo_today_rows || []) : (isBesok ? (ws.wo_besok_rows || []) : (ws.waiting_wo_rows || []));
                if (!src.length) return null;
                const besokRng = ws.besok_range_label || ('>= ' + ws.besok_label);
                const todayCols = Array.isArray(ws.wo_today_columns) ? ws.wo_today_columns : [];
                let idxSaCol = -1;
                let cols;
                if (isToday) {
                    const dispSt = todayCols.map(c => (String(c).toLowerCase() === 'active' ? 'Active (SA)' : c));
                    if (dispSt.indexOf('Active (SA)') >= 0) idxSaCol = 2 + dispSt.indexOf('Active (SA)');
                    cols = ['Sales Leader', 'Salesname', ...dispSt, 'Grand Total'];
                } else {
                    cols = ['Sales Leader', 'Salesname', 'Grand Total'];
                }
                const rows = [];
                const rStyles = [];
                let idxGtP = -1;
                for (const r of src) {
                    const rt = r.row_type || 'agent';
                    if (rt === 'grand_total') { idxGtP = rows.length; rStyles.push({ bg: '#fef3c7', bold: true }); }
                    else if (rt === 'leader_total') { rStyles.push({ bg: '#dbeafe', bold: true }); }
                    else { rStyles.push(null); }
                    const ldrC = (rt === 'agent') ? r.leader : '';
                    if (isToday) {
                        const stMap = r.statuses || {};
                        const stVals = todayCols.map(c => {
                            const v = Number(stMap[c] || 0);
                            return (v > 0 || rt === 'grand_total') ? fmtInt(v) : '';
                        });
                        rows.push([ldrC, r.salesname, ...stVals, fmtInt(r.total)]);
                    } else {
                        rows.push([ldrC, r.salesname, fmtInt(r.total)]);
                    }
                }
                const title = isToday
                    ? `1. WO TODAY (${ws.today_label}) — DETAIL PER AGENT & SA`
                    : (isBesok ? `2. WO BESOK (${besokRng}) — JADWAL INSTALASI` : `3. WAITING WO (INSTALASI BLANK) — DETAIL PER AGENT`);
                const sub = isToday
                    ? `Count of Customer Name pada Instalasi Date ${ws.today_label} (Status = ALL, Active = SA)`
                    : (isBesok ? `Instalasi Date > ${ws.today_label} (Multiple Items, Status = ALL)` : `Instalasi Date = (blank) | Status: Back To Sales, READY, Reschedule, Waiting WO`);
                const headBg = isToday ? '#002060' : (isBesok ? '#065f46' : '#92400e');
                const alignArr = isToday ? ['l', 'l', ...todayCols.map(() => 'c'), 'c'] : ['l', 'l', 'c'];
                const imgP = await renderTablePng({
                    title, subtitle: sub, columns: cols, headBg, rows,
                    align: alignArr,
                    rowStyles: rStyles,
                    cellStyle: (i, c) => {
                        if (c === cols.length - 1) return { bold: true, bg: i === idxGtP ? '#fef3c7' : undefined };
                        if (idxSaCol >= 0 && c === idxSaCol) return { bold: true, bg: i === idxGtP ? '#bbf7d0' : '#f0fdf4', fg: '#166534' };
                        return null;
                    },
                    notes: [`Total baris pivot: ${rows.length}`],
                });
                const fName = isToday ? `01C1_WO_TODAY_${ws.today_label}.png` : (isBesok ? `01C2_WO_BESOK_${ws.besok_label}.png` : `01C3_WAITING_WO_${ws.today_label}.png`);
                const cap = isToday ? `1️⃣ <b>WO TODAY (${ws.today_label}) — Detail Agent &amp; SA</b>` : (isBesok ? `2️⃣ <b>WO BESOK (${besokRng}) — Detail Agent</b>` : `3️⃣ <b>WAITING WO (Instalasi Blank) — Detail Agent</b>`);
                return { fileName: fName, caption: cap, blob: imgP.blob, dataUrl: imgP.dataUrl };
            }

            async function renderWoTeamPngs(ws) {
                const agList = ws.agent_summary || [];
                if (!agList.length) return [];
                const besokRng = ws.besok_range_label || ('>= ' + ws.besok_label);
                const byLdrW = new Map();
                for (const a of agList) {
                    if (!byLdrW.has(a.leader)) byLdrW.set(a.leader, []);
                    byLdrW.get(a.leader).push(a);
                }
                const resList = [];
                let seqW = 1;
                for (const [ldrW, grpW] of byLdrW.entries()) {
                    const rows = [], rStyles = [];
                    let sTot = 0, sSa = 0, sOn = 0, sRes = 0, sWt = 0, sOth = 0, sBsk = 0, sWwo = 0;
                    grpW.forEach((r, idx) => {
                        const cTot = Number(r.today_total || 0), cSa = Number(r.today_sa || 0);
                        const cOn = Number(r.today_on_installation || 0), cRes = Number(r.today_reschedule || 0);
                        const cWt = Number(r.today_waiting_wo || 0), cOth = Number(r.today_other || 0);
                        const cBsk = Number(r.wo_besok || 0), cWwo = Number(r.waiting_wo || 0);
                        sTot += cTot; sSa += cSa; sOn += cOn; sRes += cRes; sWt += cWt; sOth += cOth; sBsk += cBsk; sWwo += cWwo;
                        rows.push([
                            String(idx + 1), r.salesname,
                            fmtInt(cTot), cSa ? fmtInt(cSa) : '-', cOn ? fmtInt(cOn) : '-',
                            cRes ? fmtInt(cRes) : '-', cWt ? fmtInt(cWt) : '-', cOth ? fmtInt(cOth) : '-',
                            fmtInt(cBsk), fmtInt(cWwo),
                        ]);
                        rStyles.push(null);
                    });
                    const idxTotW = rows.length;
                    rows.push(['', `TOTAL ${ldrW}`, fmtInt(sTot), fmtInt(sSa), fmtInt(sOn), fmtInt(sRes), fmtInt(sWt), fmtInt(sOth), fmtInt(sBsk), fmtInt(sWwo)]);
                    rStyles.push({ bg: '#dbeafe', bold: true });
                    const imgT = await renderTablePng({
                        title: `WORK ORDER AGENT — TIM ${ldrW.toUpperCase()}`,
                        subtitle: `1. WO Today (${ws.today_label} + SA)  •  2. WO Besok (${besokRng})  •  3. Waiting WO (Blank)`,
                        columns: ['NO', 'SALESNAME', 'TOTAL\nTODAY', 'SA\n(ACTIVE)', 'ON\nINSTALL', 'RESCHED', 'WAIT\nWO', 'LAINNYA', `BESOK\n(${besokRng})`, 'WAITING\nWO'],
                        groupHeaders: [
                            { label: `1. WO TODAY (${ws.today_label})`, start: 2, end: 7, bg: '#002060' },
                            { label: '2. BESOK & 3. WAITING WO', start: 8, end: 9, bg: '#065f46' },
                        ],
                        rows, align: ['c', 'l', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'], rowStyles: rStyles,
                        cellStyle: (i, c) => {
                            if (c === 2) return i === idxTotW ? { bg: '#c9daf8', fg: '#1e3a8a', bold: true } : { bg: '#eff6ff', bold: true };
                            if (c === 3) return i === idxTotW ? { bg: '#bbf7d0', fg: '#14532d', bold: true } : { bg: '#f0fdf4', fg: '#166534', bold: true };
                            if (c === 8) return i === idxTotW ? { bg: '#d1fae5', fg: '#065f46', bold: true } : { bg: '#ecfdf5', bold: true };
                            if (c === 9) return i === idxTotW ? { bg: '#fde68a', fg: '#92400e', bold: true } : { bg: '#fffbeb', bold: true };
                            return null;
                        },
                        notes: [`Tim ${ldrW}: WO Today=${sTot} (SA=${sSa}) | WO Besok=${sBsk} | Waiting WO=${sWwo}`],
                    });
                    const safeLw = ldrW.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '');
                    const escLw = ldrW.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    resList.push({
                        fileName: `01D_${String(seqW).padStart(2, '0')}_WO_Tim_${safeLw}.png`,
                        caption: `🛠️ <b>WO Detail Agent — Tim ${escLw}</b> | Today (${ws.today_label}): ${sTot} (SA ${sSa}) | Besok: ${sBsk} | Waiting: ${sWwo}`,
                        blob: imgT.blob,
                        dataUrl: imgT.dataUrl,
                    });
                    seqW++;
                }
                return resList;
            }

            async function buildWoTableAndTeamPngs(ws, includeCards) {
                const woOut = [];
                const besokRng = ws.besok_range_label || ('>= ' + ws.besok_label);
                if (ws.leader_summary && ws.leader_summary.length) {
                    const wRows = [], wStyles = [];
                    let idxGtW = -1;
                    for (const wr of ws.leader_summary) {
                        if (wr.is_gt) { idxGtW = wRows.length; wStyles.push({ bg: '#dbeafe', bold: true }); }
                        else { wStyles.push(null); }
                        wRows.push([
                            wr.leader, fmtInt(wr.today_total || 0), fmtInt(wr.today_sa || 0),
                            fmtInt(wr.today_on_installation || 0), fmtInt(wr.today_reschedule || 0),
                            fmtInt(wr.today_waiting_wo || 0), fmtInt(wr.today_other || 0),
                            fmtInt(wr.wo_besok || 0), fmtInt(wr.waiting_wo || 0),
                        ]);
                    }
                    const imgWo = await renderTablePng({
                        title: `MONITORING WORK ORDER (${ws.today_label} | WO BESOK | WAITING WO)`,
                        subtitle: `1. WO TODAY (${ws.today_label} + SA Active)  •  2. WO BESOK (${besokRng}, Status ALL)  •  3. WAITING WO (Blank)`,
                        columns: ['Sales Leader', 'TOTAL\nTODAY', 'SA\n(ACTIVE)', 'ON\nINSTALL', 'RESCHED', 'WAIT\nWO', 'LAINNYA', `WO BESOK\n(${besokRng})`, 'WAITING WO\n(BLANK)'],
                        groupHeaders: [
                            { label: `1. WO TODAY (${ws.today_label})`, start: 1, end: 6, bg: '#002060' },
                            { label: '2. BESOK & 3. WAITING WO', start: 7, end: 8, bg: '#065f46' },
                        ],
                        headBg: '#002060', rows: wRows, align: ['l', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'], rowStyles: wStyles,
                        cellStyle: (i, c) => {
                            if (i === idxGtW && c === 1) return { bg: '#c9daf8', fg: '#1e3a8a', bold: true };
                            if (i === idxGtW && c === 2) return { bg: '#bbf7d0', fg: '#14532d', bold: true };
                            if (i === idxGtW && c === 7) return { bg: '#d1fae5', fg: '#065f46', bold: true };
                            if (i === idxGtW && c === 8) return { bg: '#fde68a', fg: '#92400e', bold: true };
                            if (c === 1) return { bg: '#eff6ff', bold: true };
                            if (c === 2) return { bg: '#f0fdf4', fg: '#166534', bold: true };
                            if (c === 7) return { bg: '#ecfdf5', bold: true };
                            if (c === 8) return { bg: '#fffbeb', bold: true };
                            return null;
                        },
                        notes: [`1. WO TODAY: Semua status pd ${ws.today_label} (Active = SA). 2. WO BESOK: Semua Instalasi Date > ${ws.today_label}. 3. WAITING WO: Instalasi Blank (Back To Sales/READY/Reschedule/Waiting WO).`],
                    });
                    woOut.push({
                        fileName: `01C_Monitoring_WO_${ws.today_label}.png`,
                        caption: `🛠️ <b>Monitoring Work Order</b> | 1. Today (${ws.today_label}) | 2. Besok (${besokRng}) | 3. Waiting WO`,
                        blob: imgWo.blob,
                        dataUrl: imgWo.dataUrl,
                    });
                }
                for (const md of ['today', 'besok', 'waiting']) {
                    const pImg = await renderWoPivotPng(ws, md);
                    if (pImg) woOut.push(pImg);
                }
                const tImgs = await renderWoTeamPngs(ws);
                for (const ti of tImgs) woOut.push(ti);
                if (includeCards && ws.agent_summary && ws.agent_summary.length) {
                    for (const ag of ws.agent_summary) {
                        woOut.push(await renderAgentWoCardPng(ag, ws.today_label, ws.besok_label));
                    }
                }
                return woOut;
            }

            if (data.wo_summary) {
                const wsItems = await buildWoTableAndTeamPngs(data.wo_summary, !!data.wo_summary.include_cards);
                for (const wi of wsItems) out.push(wi);
            }

            // 2. DETAIL AGENT PER LEADER (TANPA Reguler/Yearly terpisah!)
            if (data.agent_rows && data.agent_rows.length) {
                const byLdr = new Map();
                for (const ag of data.agent_rows) {
                    if (!byLdr.has(ag.leader)) byLdr.set(ag.leader, []);
                    byLdr.get(ag.leader).push(ag);
                }
                let seq = 2;
                for (const [ldrName, grp] of byLdr.entries()) {
                    const rows = [];
                    const styles = [];
                    const vacantSet = new Set();
                    const kurangSet = new Set();
                    let nKurang = 0;
                    let sT = 0, sSa = 0, sPaid = 0, sM = 0, s3m = 0, sSem = 0, sYr = 0, sPHr = 0, sSHr = 0;

                    grp.forEach((r, idx) => {
                        const isVac = String(r.name).toUpperCase() === 'VACANT';
                        let stTxt = 'AMAN';
                        if (isVac) {
                            stTxt = 'VACANT';
                            vacantSet.add(rows.length);
                        } else if (r.persen < data.target_mtd) {
                            stTxt = `KURANG -${data.target_mtd - r.persen}%`;
                            nKurang++;
                            kurangSet.add(rows.length);
                        }
                        sT += r.target_all; sSa += r.sa_nov; sPaid += r.paid_nov;
                        sM += r.p_m; s3m += r.p_3m; sSem += r.p_sem; sYr += r.p_yr;
                        sPHr += r.harus_paid_hr; sSHr += r.harus_sa_hr;
                        rows.push([
                            String(idx + 1), r.name, r.level, fmtInt(r.target_all),
                            fmtInt(r.sa_nov), fmtInt(r.paid_nov), fmtInt(r.gap_sa), r.persen + '%',
                            fmtInt(r.runrate_30), fmtInt(r.p_m), fmtInt(r.p_3m), fmtInt(r.p_sem), fmtInt(r.p_yr),
                            stTxt, fmtInt(r.harus_paid_hr), fmtInt(r.harus_sa_hr),
                        ]);
                        styles.push(null);
                    });

                    const idxTotL = rows.length;
                    const pctL = sT > 0 ? roundExcel((sSa / sT) * 100) : 0;
                    const rrL = roundExcel((sSa * data.total_hari) / Math.max(1, data.hari));
                    rows.push([
                        '', `TOTAL ${ldrName}`, '', fmtInt(sT), fmtInt(sSa), fmtInt(sPaid), fmtInt(sSa - sT),
                        pctL + '%', fmtInt(rrL), fmtInt(sM), fmtInt(s3m), fmtInt(sSem), fmtInt(sYr),
                        `${nKurang} agen kurang`, fmtInt(sPHr), fmtInt(sSHr),
                    ]);
                    styles.push({ bg: '#b4a7d6', bold: true });

                    const imgLdr = await renderTablePng({
                        title: `DETAIL AGENT — TIM ${ldrName.toUpperCase()}`,
                        subtitle: `Realisasi MTD 1-${data.hari} ${data.bln_ini} ${data.tahun}  •  Sisa ${data.sisa_hari} hari  •  Target MTD ${data.target_mtd}%`,
                        columns: ['NO', 'SALES NAME', 'LEVEL', 'TARGET\nTOTAL', `SA\n${data.bln_ini}`, `PAID\n${data.bln_ini}`, 'GAP\nSA', 'PERSEN-\nTASE', `RUNRATE\n${data.total_hari}H`, 'M', '3M', 'SEM', 'Y', `STATUS vs\nTARGET ${data.target_mtd}%`, 'PAID\n/ HARI', 'SA\n/ HARI'],
                        groupHeaders: [
                            { label: 'BREAKDOWN PAKET', start: 9, end: 12, bg: '#1f3864' },
                            { label: 'KUOTA WAJIB / HARI', start: 14, end: 15, bg: '#1f3864' },
                        ],
                        banner: { top: 'TARGET', left: data.periode, right: data.target_mtd + '%' },
                        rows: rows,
                        align: ['c', 'l', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c', 'c'],
                        rowStyles: styles,
                        cellStyle: (i, c, txt) => {
                            const isTot = i === idxTotL;
                            if (c === 1 && vacantSet.has(i)) return { bg: '#ffff00', bold: true };
                            if (c === 4 && !isTot) return { bg: '#c9daf8', bold: true };
                            if (c === 6 && !isTot && Number(String(txt).replace(/\./g, '')) < 0) return { fg: '#990000' };
                            if (c === 7) {
                                const v = parseInt(String(txt), 10);
                                return (!isNaN(v) && v < data.target_mtd)
                                    ? { bg: '#f4cccc', fg: '#990000', bold: true }
                                    : { bg: '#d9ead3', fg: '#134f5c', bold: true };
                            }
                            if (c === 13 && !isTot) {
                                if (String(txt).startsWith('KURANG')) return { bg: '#f4cccc', fg: '#990000', bold: true };
                                if (txt === 'AMAN') return { bg: '#d9ead3', fg: '#134f5c', bold: true };
                            }
                            if ((c === 14 || c === 15) && kurangSet.has(i)) return { bg: '#fff2cc', fg: '#7f4f00', bold: true };
                            if (c === 14 || c === 15) return { bold: true };
                            return null;
                        },
                        notes: [`PERSENTASE = SA ÷ Target Total. Kuning = kuota harian Paid/SA bagi agen di bawah ${data.target_mtd}%.`],
                    });
                    const safeL = ldrName.replace(/[^A-Za-z0-9]+/g, '_').replace(/^_|_$/g, '');
                    const escCapL = ldrName.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    out.push({
                        fileName: `${String(seq).padStart(2, '0')}_Detail_Agent_${safeL}.png`,
                        caption: `📋 <b>Detail Agent — Tim ${escCapL}</b> | ${data.periode} | Target MTD ${data.target_mtd}%`,
                        blob: imgLdr.blob,
                        dataUrl: imgLdr.dataUrl,
                    });
                    seq++;
                }
            }
            return out;
        }

        function appendImageGrid(container, imgs, gridClass) {
            const grid = document.createElement('div');
            grid.className = gridClass || 'wo-img-grid';
            for (const im of imgs) {
                const card = document.createElement('div');
                card.className = 'wo-img-card';
                const bar = document.createElement('div');
                bar.style.cssText = 'display:flex; justify-content:space-between; align-items:center; gap:8px; flex-wrap:wrap;';
                const ttl = document.createElement('b');
                ttl.style.fontSize = '0.82rem';
                ttl.textContent = im.fileName;
                const dl = document.createElement('a');
                dl.href = im.dataUrl;
                dl.download = im.fileName;
                dl.className = 'btn btn-green';
                dl.style.cssText = 'padding:5px 10px; font-size:0.78rem;';
                dl.textContent = '📥 Download .png';
                bar.appendChild(ttl);
                bar.appendChild(dl);
                const imgEl = document.createElement('img');
                imgEl.src = im.dataUrl;
                imgEl.alt = im.fileName;
                card.appendChild(bar);
                card.appendChild(imgEl);
                grid.appendChild(card);
            }
            container.appendChild(grid);
        }

        function buildStoredZipBlob(files) {
            const crcTable = new Uint32Array(256);
            for (let n = 0; n < 256; n++) {
                let c = n;
                for (let k = 0; k < 8; k++) c = (c & 1) ? (0xedb88320 ^ (c >>> 1)) : (c >>> 1);
                crcTable[n] = c >>> 0;
            }
            const crc32 = (u8) => {
                let c = 0xffffffff;
                for (let i = 0; i < u8.length; i++) c = crcTable[(c ^ u8[i]) & 0xff] ^ (c >>> 8);
                return (c ^ 0xffffffff) >>> 0;
            };
            const enc = new TextEncoder();
            const parts = [];
            const central = [];
            let offset = 0;
            for (const f of files) {
                const nameB = enc.encode(f.name);
                const data = f.bytes;
                const crc = crc32(data);
                const lfh = new Uint8Array(30 + nameB.length);
                const dv = new DataView(lfh.buffer);
                dv.setUint32(0, 0x04034b50, true); dv.setUint16(4, 20, true);
                dv.setUint16(8, 0, true); dv.setUint32(14, crc, true);
                dv.setUint32(18, data.length, true); dv.setUint32(22, data.length, true);
                dv.setUint16(26, nameB.length, true);
                lfh.set(nameB, 30);
                parts.push(lfh, data);

                const cdh = new Uint8Array(46 + nameB.length);
                const cv = new DataView(cdh.buffer);
                cv.setUint32(0, 0x02014b50, true); cv.setUint16(4, 20, true); cv.setUint16(6, 20, true);
                cv.setUint32(16, crc, true); cv.setUint32(20, data.length, true); cv.setUint32(24, data.length, true);
                cv.setUint16(28, nameB.length, true); cv.setUint32(42, offset, true);
                cdh.set(nameB, 46);
                central.push(cdh);
                offset += lfh.length + data.length;
            }
            let cdSize = 0;
            for (const ch of central) { parts.push(ch); cdSize += ch.length; }
            const eocd = new Uint8Array(22);
            const ev = new DataView(eocd.buffer);
            ev.setUint32(0, 0x06054b50, true);
            ev.setUint16(8, files.length, true); ev.setUint16(10, files.length, true);
            ev.setUint32(12, cdSize, true); ev.setUint32(16, offset, true);
            parts.push(eocd);
            return new Blob(parts, { type: 'application/zip' });
        }

        function getWoFilteredAgents() {
            const ws = (PREVIEW_DATA && PREVIEW_DATA.wo_summary) ? PREVIEW_DATA.wo_summary : null;
            if (!ws || !ws.agent_summary) return [];
            const selL = document.getElementById('wo-card-ldr-filter');
            const selA = document.getElementById('wo-card-ag-filter');
            const fLdr = selL ? selL.value : 'ALL';
            const fAg = selA ? selA.value : 'ALL';
            return ws.agent_summary.filter(a => {
                if (fLdr !== 'ALL' && a.leader !== fLdr) return false;
                if (fAg !== 'ALL' && `${a.leader}||${a.salesname}` !== fAg) return false;
                return true;
            });
        }

        function woInitDropdowns() {
            const selL = document.getElementById('wo-card-ldr-filter');
            const selA = document.getElementById('wo-card-ag-filter');
            const ws = (PREVIEW_DATA && PREVIEW_DATA.wo_summary) ? PREVIEW_DATA.wo_summary : null;
            if (!selL || !selA || !ws || !ws.agent_summary) return;
            if (selL.dataset.initDone) return;
            selL.dataset.initDone = '1';
            const ldrSet = [...new Set(ws.agent_summary.map(a => a.leader))];
            for (const l of ldrSet) {
                const op = document.createElement('option');
                op.value = l; op.textContent = l;
                selL.appendChild(op);
            }
            window.woPopulateAgentSelect();
        }

        window.woPopulateAgentSelect = function() {
            const selL = document.getElementById('wo-card-ldr-filter');
            const selA = document.getElementById('wo-card-ag-filter');
            const ws = (PREVIEW_DATA && PREVIEW_DATA.wo_summary) ? PREVIEW_DATA.wo_summary : null;
            if (!selL || !selA || !ws || !ws.agent_summary) return;
            const fLdr = selL.value;
            selA.innerHTML = '<option value="ALL">👥 Semua Agent Terpilih</option>';
            for (const a of ws.agent_summary) {
                if (fLdr !== 'ALL' && a.leader !== fLdr) continue;
                const op = document.createElement('option');
                op.value = `${a.leader}||${a.salesname}`;
                op.textContent = `${a.salesname} (${a.leader})`;
                selA.appendChild(op);
            }
        };

        window.woOpenGalleryTab = async function(btnEl) {
            window.switchWoTab('wo-tab-gallery', btnEl);
            woInitDropdowns();
            const tbDiv = document.getElementById('wo-gal-tables');
            if (tbDiv && !tbDiv.dataset.rendered) {
                await window.woRenderTableGallery();
            }
        };

        window.woRenderTableGallery = async function() {
            const box = document.getElementById('wo-gal-tables');
            const ws = (PREVIEW_DATA && PREVIEW_DATA.wo_summary) ? PREVIEW_DATA.wo_summary : null;
            if (!box || !ws) return;
            box.innerHTML = '<div style="padding:10px; color:#1e3a8a; font-weight:700;">⏳ Merender foto Ringkasan, Pivot 1/2/3 &amp; Tim per Leader...</div>';
            try {
                // Gunakan buildAllReportPngs-style WO subset (Ringkasan + Pivot + Tim)
                const prevClone = Object.assign({}, PREVIEW_DATA, { mtd_rows: [], daily_rows: [], agent_rows: [] });
                if (prevClone.wo_summary) prevClone.wo_summary = Object.assign({}, prevClone.wo_summary, { include_cards: false });
                const imgs = await buildAllReportPngs(prevClone);
                box.innerHTML = '<b>📸 Foto Ringkasan, Detail Pivot &amp; Setiap Tim Leader (' + imgs.length + ' Foto PNG):</b>';
                appendImageGrid(box, imgs, 'wo-img-grid');
                box.dataset.rendered = '1';
            } catch (err) {
                box.innerHTML = '<div class="alert-err">❌ Gagal merender foto WO: ' + err.message + '</div>';
            }
        };

        async function renderAgentCardsBatch(agList, todayLbl, besokLbl) {
            const imgs = [];
            for (const ag of agList) {
                imgs.push(await renderAgentWoCardPng(ag, todayLbl, besokLbl));
            }
            return imgs;
        }

        window.woRenderAgentCards = async function() {
            woInitDropdowns();
            const box = document.getElementById('wo-gal-agents');
            const ws = (PREVIEW_DATA && PREVIEW_DATA.wo_summary) ? PREVIEW_DATA.wo_summary : null;
            if (!box || !ws) return;
            const list = getWoFilteredAgents();
            if (!list.length) {
                box.innerHTML = '<div class="alert-err">ℹ️ Tidak ada agen pada filter yang dipilih.</div>';
                return;
            }
            box.innerHTML = '<div style="padding:10px; color:#92400e; font-weight:700;">⏳ Merender ' + list.length + ' foto kartu WO masing-masing agent...</div>';
            const imgs = await renderAgentCardsBatch(list, ws.today_label, ws.besok_label);
            box.innerHTML = '<b>👤 Foto Kartu Masing-Masing Agent (' + imgs.length + ' Foto PNG):</b>';
            appendImageGrid(box, imgs, 'wo-card-grid');
        };

        window.woDownloadZip = async function(kind) {
            woInitDropdowns();
            const ws = (PREVIEW_DATA && PREVIEW_DATA.wo_summary) ? PREVIEW_DATA.wo_summary : null;
            if (!ws) return;
            let imgs = [];
            let zipName = `Foto_WO_${ws.today_label}.zip`;
            if (kind === 'tables') {
                const prevClone = Object.assign({}, PREVIEW_DATA, { mtd_rows: [], daily_rows: [], agent_rows: [] });
                if (prevClone.wo_summary) prevClone.wo_summary = Object.assign({}, prevClone.wo_summary, { include_cards: false });
                imgs = await buildAllReportPngs(prevClone);
                zipName = `Foto_WO_Ringkasan_Pivot_Tim_${ws.today_label}.zip`;
            } else {
                const list = getWoFilteredAgents();
                imgs = await renderAgentCardsBatch(list, ws.today_label, ws.besok_label);
                zipName = `Foto_WO_Masing_Masing_Agent_${ws.today_label}.zip`;
            }
            if (!imgs.length) return;
            const files = [];
            for (const im of imgs) {
                const buf = await im.blob.arrayBuffer();
                files.push({ name: im.fileName, bytes: new Uint8Array(buf) });
            }
            const zBlob = buildStoredZipBlob(files);
            const url = URL.createObjectURL(zBlob);
            const a = document.createElement('a');
            a.href = url; a.download = zipName;
            document.body.appendChild(a); a.click(); a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 5000);
        };

        window.renderPersonalWoCard = async function() {
            const box = document.getElementById('agen-wo-card-box');
            const ws = (PREVIEW_DATA && PREVIEW_DATA.wo_summary) ? PREVIEW_DATA.wo_summary : null;
            if (!box || !ws || !ws.agent_summary || !ws.agent_summary.length) return;
            box.style.display = 'block';
            box.innerHTML = '<div style="color:#fde047; font-weight:700;">⏳ Menyiapkan foto kartu WO Anda...</div>';
            const imgs = await renderAgentCardsBatch(ws.agent_summary, ws.today_label, ws.besok_label);
            box.innerHTML = '';
            appendImageGrid(box, imgs, 'wo-card-grid');
        };

        window.tgPreviewGallery = async function() {
            const gal = document.getElementById('tg-preview-gallery');
            if (!gal) return;
            gal.style.display = 'block';
            gal.innerHTML = '<div style="padding:10px; color:#1e3a8a; font-weight:700;">⏳ Merender seluruh gambar tabel presentasi &amp; WO (.png)...</div>';
            try {
                const prevCopy = Object.assign({}, PREVIEW_DATA);
                const incCardEl = document.querySelector('input[name="include_wo_cards"]');
                const incWoEl = document.querySelector('input[name="include_wo"]');
                if (!incWoEl || !incWoEl.checked) {
                    prevCopy.wo_summary = null;
                } else if (prevCopy.wo_summary) {
                    prevCopy.wo_summary = Object.assign({}, prevCopy.wo_summary, { include_cards: !!(incCardEl && incCardEl.checked) });
                }
                const imgs = await buildAllReportPngs(prevCopy);
                gal.innerHTML = '<h4 style="margin:0 0 10px 0;">🖼️ Pratinjau Semua Gambar Presentasi &amp; WO (' + imgs.length + ' Gambar PNG)</h4>';
                appendImageGrid(gal, imgs, 'wo-img-grid');
            } catch (err) {
                gal.innerHTML = '<div class="alert-err">❌ Gagal membuat pratinjau gambar: ' + err.message + '</div>';
            }
        };

        async function uploadSinglePng(cfg, im, progEl) {
            const tryEndpoint = async (mode) => {
                for (let att = 0; att < 3; att++) {
                    const fd = new FormData();
                    fd.append('chat_id', cfg.chat_id);
                    fd.append('caption', im.caption);
                    fd.append('parse_mode', 'HTML');
                    fd.append(mode === 'document' ? 'document' : 'photo', im.blob, im.fileName);
                    const ep = mode === 'document' ? '/sendDocument' : '/sendPhoto';
                    const r = await fetchWithTimeout(cfg.api_base + ep, { method: 'POST', body: fd }, 14000);
                    const j = await r.json().catch(() => null);
                    if (r.status === 429 && j && j.parameters && j.parameters.retry_after) {
                        const waitMs = Math.min((Number(j.parameters.retry_after) + 1) * 1000, 15000);
                        if (progEl) progEl.textContent = '⏳ Telegram limit 429 — jeda ' + Math.round(waitMs / 1000) + ' detik sebelum lanjut...';
                        await new Promise(rs => setTimeout(rs, waitMs));
                        continue;
                    }
                    return { ok: !!(r.ok && j && j.ok), status: r.status, desc: (j && j.description) ? j.description : ('HTTP ' + r.status) };
                }
                return { ok: false, status: 429, desc: 'Rate limit 429 Telegram' };
            };

            try {
                let res = await tryEndpoint(cfg.img_mode);
                const dLow = (res.desc || '').toLowerCase();
                if (!res.ok && cfg.img_mode === 'photo' && res.status === 400 && !dLow.includes('chat not found') && !dLow.includes('forbidden')) {
                    res = await tryEndpoint('document');
                }
                if (res.ok) return res;
                throw new Error(res.desc);
            } catch (browserErr) {
                const fdSrv = new FormData();
                fdSrv.append('action', 'send_telegram_blob');
                fdSrv.append('csrf_token', cfg.csrf_token);
                fdSrv.append('chat_id', cfg.chat_id);
                fdSrv.append('caption', im.caption);
                fdSrv.append('img_mode', cfg.img_mode);
                fdSrv.append('png_file', im.blob, im.fileName);
                const rs = await fetchWithTimeout('index.php', { method: 'POST', body: fdSrv }, 15000);
                const js = await rs.json().catch(() => null);
                if (js && js.ok) return { ok: true };
                throw new Error(browserErr.message || (js && js.description) || 'Gagal mengunggah gambar ke Telegram');
            }
        }

        if (window.__TG_SEND_CFG) {
            window.__TG_ABORT = false;
            (async function(){
                const cfg = window.__TG_SEND_CFG;
                const box = document.getElementById('tg-relay-box');
                const prog = document.getElementById('tg-relay-progress');
                let sentImgs = 0, sentMsgs = 0;
                try {
                    if (cfg.send_images && cfg.visual_data) {
                        const imgs = await buildAllReportPngs(cfg.visual_data);
                        const delayMs = imgs.length > 20 ? 950 : 380;
                        for (let i = 0; i < imgs.length; i++) {
                            if (window.__TG_ABORT) throw new Error('Pengiriman dibatalkan oleh pengguna.');
                            if (prog) prog.textContent = '🖼️ Mengunggah gambar ' + (i + 1) + '/' + imgs.length + ': ' + imgs[i].fileName + '...';
                            await uploadSinglePng(cfg, imgs[i], prog);
                            sentImgs++;
                            await new Promise(r => setTimeout(r, delayMs));
                        }
                    }
                    if (cfg.send_text && cfg.messages && cfg.messages.length) {
                        for (let j = 0; j < cfg.messages.length; j++) {
                            if (window.__TG_ABORT) throw new Error('Pengiriman dibatalkan oleh pengguna.');
                            if (prog) prog.textContent = '📝 Mengirim teks bagian ' + (j + 1) + '/' + cfg.messages.length + '...';
                            for (let att = 0; att < 3; att++) {
                                const fdTxt = new URLSearchParams({
                                    chat_id: cfg.chat_id,
                                    text: cfg.messages[j],
                                    parse_mode: 'HTML',
                                    disable_web_page_preview: 'true'
                                });
                                const rt = await fetchWithTimeout(cfg.api_base + '/sendMessage', { method: 'POST', body: fdTxt }, 8000);
                                const jt = await rt.json().catch(() => null);
                                if (rt.status === 429 && jt && jt.parameters && jt.parameters.retry_after) {
                                    const waitMs = Math.min((Number(jt.parameters.retry_after) + 1) * 1000, 15000);
                                    if (prog) prog.textContent = '⏳ Telegram limit 429 — jeda ' + Math.round(waitMs / 1000) + ' detik...';
                                    await new Promise(rs => setTimeout(rs, waitMs));
                                    continue;
                                }
                                if (!rt.ok || !jt || !jt.ok) {
                                    throw new Error((jt && jt.description) ? jt.description : ('HTTP ' + rt.status));
                                }
                                break;
                            }
                            sentMsgs++;
                            await new Promise(r => setTimeout(r, 280));
                        }
                    }
                    if (box) {
                        box.className = 'alert-ok';
                        box.style.background = ''; box.style.color = ''; box.style.borderColor = '';
                        box.innerHTML = '✅ <b>BERHASIL TERKIRIM KE TELEGRAM!</b> Chat ID <b>' + cfg.chat_id + '</b> (' + sentImgs + ' Gambar Tabel PNG' + (cfg.send_text ? (' + ' + sentMsgs + ' Pesan Teks') : '') + ').';
                    }
                } catch (err) {
                    if (box) {
                        box.className = 'alert-err';
                        box.style.background = ''; box.style.color = ''; box.style.borderColor = '';
                        box.innerHTML = '❌ <b>Gagal mengirim ke Telegram:</b> ' + err.message + '<br><small>Pastikan Chat ID benar dan bot <b>@NoticeTelesalesbot</b> sudah diklik <b>/start</b> atau ditambahkan ke grup tujuan.</small>';
                    }
                }
            })();
        }
    })();
    </script>
<?php endif; ?>
</div>
</body>
</html>
"""

    kode_php = (
        kode_php.replace("__SA_USER__", str(cfg_sa["username"]))
        .replace("__SA_SALT__", str(cfg_sa["salt"]))
        .replace("__SA_ITER__", str(int(cfg_sa["iterations"])))
        .replace("__SA_HASH__", str(cfg_sa["hash"]))
    )

    path_index = os.path.join(FOLDER_CPANEL, "index.php")
    with open(path_index, "w", encoding="utf-8") as f:
        f.write(kode_php.lstrip())

    # 8. Paketkan seluruh cpanel_public_html ke dalam UPLOAD_KE_CPANEL_PUBLIC_HTML.zip & PATCH_UPDATE_AMAN_TANPA_HAPUS_DATA.zip
    with zipfile.ZipFile(PATH_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(FOLDER_CPANEL):
            for file in files:
                if file.startswith("tmp_prospect_") or file in (".waf_ratelimit.json", "security_audit.log"):
                    continue
                abs_p = os.path.join(root, file)
                rel_p = os.path.relpath(abs_p, FOLDER_CPANEL).replace("\\", "/")
                zf.write(abs_p, arcname=rel_p)

    path_patch_safe = os.path.join(FOLDER_PROYEK, "PATCH_UPDATE_AMAN_TANPA_HAPUS_DATA.zip")
    with zipfile.ZipFile(path_patch_safe, "w", zipfile.ZIP_DEFLATED) as zp:
        for rel_nm in ("index.php", "engine.php", ".user.ini", ".htaccess"):
            src_f = os.path.join(FOLDER_CPANEL, rel_nm)
            if os.path.isfile(src_f):
                zp.write(src_f, arcname=rel_nm)

    path_patch_idx = os.path.join(FOLDER_PROYEK, "PATCH_TELEGRAM_INDEX_ONLY.zip")
    with zipfile.ZipFile(path_patch_idx, "w", zipfile.ZIP_DEFLATED) as zi:
        zi.write(path_index, arcname="index.php")

    print("✅ Paket cPanel Lengkap berhasil dibuat!")
    print(f"   - .htaccess       : {path_htaccess}")
    print(f"   - .user.ini       : {path_user_ini}")
    print(f"   - engine.php      : {path_engine_dst}")
    print(f"   - index.php       : {path_index}")
    print(f"   - data_komisi.json: {path_json}")
    print(f"   - Uploads Store   : {FOLDER_UPLOADS}")
    print(f"   - ZIP Lengkap     : {PATH_ZIP} ({round(os.path.getsize(PATH_ZIP)/1024, 1)} KB)")
    print(f"   - PATCH AMAN      : {path_patch_safe} ({round(os.path.getsize(path_patch_safe)/1024, 1)} KB)")


if __name__ == "__main__":
    buat_paket_cpanel()
