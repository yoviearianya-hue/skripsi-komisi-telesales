<?php
/**
 * MESIN PENGOLAH DATA (Port PHP dari app.py) — Sistem Komisi & Monitoring Telesales ISP
 *
 * Membaca:
 *   1. File Target  (.xlsx)  -> blok TEAM / NAMA / LEVEL / Reguler / Yearly (sheet misal NOVEMBER'26)
 *   2. File Prospect (.xls berformat HTML dari sistem, atau .xlsx)
 * Menghitung: MTD SA per Leader, Detail Agent (SA/Paid/SO, Persentase, Harus Paid & SA per hari/minggu,
 *   Runrate, Breakdown Paket, Estimasi Komisi) dengan rumus yang sama persis dengan versi Python.
 */

if (!defined('APP_BOOT')) {
    http_response_code(403);
    exit('Forbidden');
}

const ALIAS_NAMA_AGEN = [
    'SANDRA MONICA APRILIA BENDSNEYDER' => 'SANDRA MONICA',
    'AHMAD MAULANA (MST 2)' => 'AHMAD MAULANA',
    'HERMANSYAH (MST)' => 'HERMANSYAH',
    'SRI WAHYUNINGSIH (MST)' => 'SRI WAHYUNINGSIH',
    'CYNDY PERTIWI NASUTION' => 'CINDY PERTIWI NASUTION',
    'PUTRI WULAN DARI' => 'PUTRI WULAN',
    'REINALDI PANDAMA R' => 'REINALDI PANDAMA RAHMAT',
    'REXY RONALD' => 'REXY RONALD WOWILING',
    'SITI SOLEHAH' => 'SITI SOLEHA',
    'YOHANES STEVEN' => 'YOHANES STEVEN S',
    'NAFFA DESTIANA PUTRI' => 'NAFA DESTIANA PUTRI',
    'PUNGKAS MUGO PRAKSOSO' => 'PUNGKAS MUGO PRAKOSO',
    'DENY R HIDAYAT' => 'DENY RAHMAT HIDAYAT',
    'DEFA DELVIANTY' => 'DEFA DELVIANTHY',
    'RIZKI DWI PUJI ASTUTI' => 'RIZKY DWI PUJI ASTUTI',
    'DEWI RATANASARI' => 'DEWI RATNASARI',
    'KHAIRANNY' => 'KHAIRRANY',
];

const ALIAS_NAMA_LEADER = [
    'MUHAMMAD REZKY JALADARA (MST)' => 'Muhammad Rezky Jaladara',
    'MUHAMMAD REZKY JALADARA' => 'Muhammad Rezky Jaladara',
];

const TEAM_EXCEL_KE_LEADER = [
    'A N I S' => 'Anis Anggraini',
    'ANIS' => 'Anis Anggraini',
    'F A H R U L' => 'Fahrul Amrin',
    'FAHRUL' => 'Fahrul Amrin',
    'YOVI' => 'Yovi Arian',
    'TIARA' => 'Tiara Muna Dayuningtyas',
    'YUDA IRAWAN' => 'Yudha Irawan',
    'YUDHA IRAWAN' => 'Yudha Irawan',
    'TIKA' => 'Tika Saraswati',
    'ALFIAN' => 'Alfian Bagus Setiawan',
    'HARO' => 'Muhammad Rezky Jaladara',
    'FIRLY' => 'Firliansyah',
    'JAROT' => 'Jarot Arie Sasmita',
    'EZA' => 'Eka Hardiansyah',
];

const AGEN_TOMMY_KE_FIRLY = [
    'AUDINA GUSLIANI',
    'MUHAMMAD INDRA PRATAMA',
    'RIKI ARDIANSYAH',
    'AULIA RACHMAYANI',
    'NOOR HAYATI',
];

const PETA_BULAN_INDO = [
    'januari' => 1, 'jan' => 1, 'februari' => 2, 'feb' => 2, 'pebruari' => 2,
    'maret' => 3, 'mar' => 3, 'april' => 4, 'apr' => 4, 'mei' => 5, 'may' => 5,
    'juni' => 6, 'jun' => 6, 'juli' => 7, 'jul' => 7,
    'agustus' => 8, 'agu' => 8, 'ags' => 8, 'agusrus' => 8, 'agutus' => 8,
    'september' => 9, 'sep' => 9, 'sept' => 9,
    'oktober' => 10, 'okt' => 10, 'oct' => 10,
    'november' => 11, 'nov' => 11, 'nopember' => 11,
    'desember' => 12, 'des' => 12, 'dec' => 12,
];

const NAMA_BULAN_SINGKAT = [
    1 => 'JAN', 2 => 'FEB', 3 => 'MAR', 4 => 'APR', 5 => 'MEI', 6 => 'JUN',
    7 => 'JUL', 8 => 'AGU', 9 => 'SEP', 10 => 'OCT', 11 => 'NOV', 12 => 'DEC',
];

const NAMA_BULAN_TAMPIL = [
    1 => 'Jan', 2 => 'Feb', 3 => 'Mar', 4 => 'Apr', 5 => 'May', 6 => 'Jun',
    7 => 'Jul', 8 => 'Aug', 9 => 'Sep', 10 => 'Oct', 11 => 'Nov', 12 => 'Dec',
];

/** Nilai teks yang oleh pandas dianggap kosong (NaN) saat membaca Excel. */
const NILAI_NA_PANDAS = [
    '', '#N/A', '#N/A N/A', '#NA', '-1.#IND', '-1.#QNAN', '-NaN', '-nan', '1.#IND', '1.#QNAN',
    '<NA>', 'N/A', 'NA', 'NULL', 'NaN', 'None', 'n/a', 'nan', 'null',
];

/* ------------------------------------------------------------------------- */
/* UTILITAS TEKS & ANGKA                                                      */
/* ------------------------------------------------------------------------- */

function u_upper(string $s): string
{
    return function_exists('mb_strtoupper') ? mb_strtoupper($s, 'UTF-8') : strtoupper($s);
}

function u_lower(string $s): string
{
    return function_exists('mb_strtolower') ? mb_strtolower($s, 'UTF-8') : strtolower($s);
}

/** Setara str.title() Python: huruf pertama tiap kata kapital, sisanya kecil. */
function u_title(string $s): string
{
    $lower = u_lower($s);
    $res = preg_replace_callback('/(?<!\p{L})\p{L}/u', function ($m) {
        return u_upper($m[0]);
    }, $lower);
    return $res === null ? $s : $res;
}

function hapus_zero_width(string $s): string
{
    $r = preg_replace('/[\x{200b}-\x{200f}\x{2060}\x{feff}]/u', '', $s);
    return $r === null ? $s : $r;
}

function rapatkan_spasi(string $s): string
{
    $r = preg_replace('/\s+/u', ' ', $s);
    return trim($r === null ? $s : $r);
}

/** Pembulatan half-up ala Excel ROUND(x,0) — identik dengan round_excel() Python. */
function round_excel($nilai): int
{
    $v = (float)$nilai;
    if (is_nan($v) || is_infinite($v)) {
        return 0;
    }
    return $v >= 0 ? (int)floor($v + 0.5) : (int)ceil($v - 0.5);
}

function normalisasi_nama_agen($nama): string
{
    if ($nama === null) {
        return '';
    }
    $teks = u_upper(rapatkan_spasi(hapus_zero_width((string)$nama)));
    return ALIAS_NAMA_AGEN[$teks] ?? $teks;
}

function normalisasi_nama_leader($nama): string
{
    if ($nama === null) {
        return '';
    }
    $teks = rapatkan_spasi((string)$nama);
    return ALIAS_NAMA_LEADER[u_upper($teks)] ?? $teks;
}

/** Setara str(x) Python untuk nilai sel Excel (float bulat -> "55.0"). */
function py_str($v): string
{
    if ($v === null) {
        return '';
    }
    if ($v instanceof DateTimeInterface) {
        return $v->format('Y-m-d H:i:s');
    }
    if (is_float($v)) {
        return floor($v) == $v && abs($v) < 1e15 ? number_format($v, 1, '.', '') : (string)$v;
    }
    if (is_bool($v)) {
        return $v ? 'True' : 'False';
    }
    return (string)$v;
}

/** Setara pd.to_numeric(errors='coerce'): null jika bukan angka. */
function ke_angka($v): ?float
{
    if ($v === null || $v instanceof DateTimeInterface) {
        return null;
    }
    if (is_int($v) || is_float($v)) {
        return (float)$v;
    }
    if (is_bool($v)) {
        return $v ? 1.0 : 0.0;
    }
    $s = trim((string)$v);
    if ($s === '' || !is_numeric($s)) {
        return null;
    }
    return (float)$s;
}

function format_rupiah($nilai): string
{
    return 'Rp ' . number_format((float)round((float)$nilai), 0, ',', '.');
}

/* ------------------------------------------------------------------------- */
/* ENKRIPSI BRANKAS VAULT (PBKDF2 + SHA256-CTR + HMAC-SHA256 — SINKRON PYTHON) */
/* ------------------------------------------------------------------------- */

function vault_turunkan_kunci(string $passwordMaster, string $saltHex): array
{
    $raw = hash_pbkdf2('sha256', $passwordMaster, $saltHex, 100000, 64, true);
    return [substr($raw, 0, 32), substr($raw, 32, 32)];
}

function vault_keystream(string $encKey, string $nonce, int $panjang): string
{
    $hasil = '';
    $counter = 0;
    while (strlen($hasil) < $panjang) {
        $hasil .= hash_hmac('sha256', $nonce . pack('N', $counter), $encKey, true);
        $counter++;
    }
    return substr($hasil, 0, $panjang);
}

function vault_encrypt_php(array $payload, string $passwordMaster, string $saltHex): string
{
    $plain = json_encode($payload, JSON_UNESCAPED_UNICODE);
    if ($plain === false) {
        $plain = '{}';
    }
    [$encKey, $macKey] = vault_turunkan_kunci($passwordMaster, $saltHex);
    $nonce = random_bytes(16);
    $ks = vault_keystream($encKey, $nonce, strlen($plain));
    $ct = $plain ^ $ks;
    $tag = hash_hmac('sha256', $nonce . $ct, $macKey, true);
    return base64_encode($nonce . $tag . $ct);
}

function vault_decrypt_php(string $vaultB64, string $passwordMaster, string $saltHex): ?array
{
    $blob = base64_decode($vaultB64, true);
    if ($blob === false || strlen($blob) < 48) {
        return null;
    }
    $nonce = substr($blob, 0, 16);
    $tag = substr($blob, 16, 32);
    $ct = substr($blob, 48);
    [$encKey, $macKey] = vault_turunkan_kunci($passwordMaster, $saltHex);
    $expectedTag = hash_hmac('sha256', $nonce . $ct, $macKey, true);
    if (!hash_equals($expectedTag, $tag)) {
        return null;
    }
    $ks = vault_keystream($encKey, $nonce, strlen($ct));
    $plain = $ct ^ $ks;
    $decoded = json_decode($plain, true);
    return is_array($decoded) ? $decoded : null;
}

/* ------------------------------------------------------------------------- */
/* PEMBACA FILE XLSX (ZipArchive + SimpleXML — tanpa library tambahan)         */
/* ------------------------------------------------------------------------- */

const NS_SS = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main';
const NS_REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships';
const NS_PKG_REL = 'http://schemas.openxmlformats.org/package/2006/relationships';

function xlsx_buka(string $path): ZipArchive
{
    if (!class_exists('ZipArchive')) {
        throw new RuntimeException('Ekstensi PHP "zip" belum aktif di hosting. Aktifkan lewat cPanel > Select PHP Version > Extensions > zip.');
    }
    $zip = new ZipArchive();
    if ($zip->open($path) !== true) {
        throw new RuntimeException('File .xlsx tidak dapat dibuka (rusak atau bukan format .xlsx yang valid).');
    }
    return $zip;
}

function xlsx_baca_xml(ZipArchive $zip, string $nama): ?SimpleXMLElement
{
    $isi = $zip->getFromName($nama);
    if ($isi === false) {
        return null;
    }
    $x = @simplexml_load_string($isi, 'SimpleXMLElement', LIBXML_NONET | LIBXML_COMPACT | LIBXML_PARSEHUGE);
    return $x === false ? null : $x;
}

/** @return array<string,string> nama sheet => path file sheet di dalam zip */
function xlsx_daftar_sheet(ZipArchive $zip): array
{
    $wb = xlsx_baca_xml($zip, 'xl/workbook.xml');
    if ($wb === null) {
        throw new RuntimeException('Struktur .xlsx tidak valid (workbook.xml tidak ditemukan).');
    }
    $rels = xlsx_baca_xml($zip, 'xl/_rels/workbook.xml.rels');
    $targetPerId = [];
    if ($rels !== null) {
        $rels->registerXPathNamespace('r', NS_PKG_REL);
        foreach ($rels->xpath('//r:Relationship') ?: [] as $rel) {
            $target = (string)$rel['Target'];
            $target = ltrim($target, '/');
            if (strpos($target, 'xl/') !== 0) {
                $target = 'xl/' . $target;
            }
            $targetPerId[(string)$rel['Id']] = $target;
        }
    }
    $wb->registerXPathNamespace('m', NS_SS);
    $hasil = [];
    foreach ($wb->xpath('//m:sheets/m:sheet') ?: [] as $sh) {
        $nama = (string)$sh['name'];
        $attrR = $sh->attributes(NS_REL);
        $rid = $attrR !== null ? (string)$attrR['id'] : '';
        if ($rid !== '' && isset($targetPerId[$rid])) {
            $hasil[$nama] = $targetPerId[$rid];
        }
    }
    return $hasil;
}

/** @return list<string> */
function xlsx_shared_strings(ZipArchive $zip): array
{
    $isi = $zip->getFromName('xl/sharedStrings.xml');
    if ($isi === false || $isi === '') {
        return [];
    }
    if (class_exists('XMLReader')) {
        $xr = new XMLReader();
        if (@$xr->XML($isi, null, LIBXML_NONET | LIBXML_COMPACT | LIBXML_PARSEHUGE)) {
            $out = [];
            $inSi = false;
            $teks = '';
            while (@$xr->read()) {
                $t = $xr->nodeType;
                if ($t === XMLReader::ELEMENT) {
                    $nm = $xr->localName;
                    if ($nm === 'si') {
                        if ($xr->isEmptyElement) {
                            $out[] = '';
                        } else {
                            $inSi = true;
                            $teks = '';
                        }
                    } elseif ($inSi && $nm === 't' && !$xr->isEmptyElement) {
                        $teks .= $xr->readString();
                    }
                } elseif ($t === XMLReader::END_ELEMENT && $xr->localName === 'si' && $inSi) {
                    $out[] = $teks;
                    $inSi = false;
                }
            }
            $xr->close();
            return $out;
        }
    }
    $ss = @simplexml_load_string($isi, 'SimpleXMLElement', LIBXML_NONET | LIBXML_COMPACT | LIBXML_PARSEHUGE);
    if ($ss === false || $ss === null) {
        return [];
    }
    $ss->registerXPathNamespace('m', NS_SS);
    $out = [];
    foreach ($ss->xpath('//m:si') ?: [] as $si) {
        $si->registerXPathNamespace('m', NS_SS);
        $teks = '';
        foreach ($si->xpath('.//m:t') ?: [] as $t) {
            $teks .= (string)$t;
        }
        $out[] = $teks;
    }
    return $out;
}

/** @return array<int,bool> indeks style (cellXfs) => apakah format tanggal */
function xlsx_style_tanggal(ZipArchive $zip): array
{
    $st = xlsx_baca_xml($zip, 'xl/styles.xml');
    if ($st === null) {
        return [];
    }
    $st->registerXPathNamespace('m', NS_SS);
    $kodeKustom = [];
    foreach ($st->xpath('//m:numFmts/m:numFmt') ?: [] as $nf) {
        $kodeKustom[(int)$nf['numFmtId']] = (string)$nf['formatCode'];
    }
    $builtinTanggal = array_merge(range(14, 22), range(27, 36), range(45, 47), range(50, 58));
    $hasil = [];
    $i = 0;
    foreach ($st->xpath('//m:cellXfs/m:xf') ?: [] as $xf) {
        $id = (int)$xf['numFmtId'];
        $adalahTanggal = in_array($id, $builtinTanggal, true);
        if (!$adalahTanggal && isset($kodeKustom[$id])) {
            $kode = preg_replace('/"[^"]*"|\[[^\]]*\]|\\\\./', '', $kodeKustom[$id]);
            $adalahTanggal = $kode !== null && preg_match('/[dmyhs]/i', $kode) === 1;
        }
        $hasil[$i++] = $adalahTanggal;
    }
    return $hasil;
}

function xlsx_serial_ke_tanggal(float $serial): DateTimeImmutable
{
    $dasar = new DateTimeImmutable('1899-12-30 00:00:00');
    $hari = (int)floor($serial);
    $detik = (int)round(($serial - $hari) * 86400);
    return $dasar->modify(sprintf('%+d days %+d seconds', $hari, $detik));
}

function xlsx_kolom_ke_indeks(string $huruf): int
{
    $n = 0;
    foreach (str_split(strtoupper($huruf)) as $ch) {
        $n = $n * 26 + (ord($ch) - 64);
    }
    return $n - 1;
}

/**
 * Membaca satu sheet .xlsx menjadi array [barisIndex0][kolomIndex0] => nilai (null/string/float/DateTimeImmutable).
 * @return array<int,array<int,mixed>>
 */
function xlsx_baca_sheet(string $path, string $namaSheet, ?array &$daftarSheet = null): array
{
    $zip = xlsx_buka($path);
    $sheets = xlsx_daftar_sheet($zip);
    $daftarSheet = array_keys($sheets);

    $kunci = null;
    $diminta = trim($namaSheet);
    if (isset($sheets[$diminta])) {
        $kunci = $diminta;
    } else {
        foreach ($sheets as $nama => $_) {
            if (u_lower(trim($nama)) === u_lower($diminta)) {
                $kunci = $nama;
                break;
            }
        }
        // Fallback pintar: jika user mengetik "NOVEMBER", cocokkan sheet terakhir yang diawali "NOVEMBER'" (mis. "NOVEMBER'26")
        if ($kunci === null && $diminta !== '') {
            foreach (array_reverse(array_keys($sheets)) as $nama) {
                $namaTrim = u_upper(trim($nama));
                $dimTrim = u_upper($diminta);
                if (str_starts_with($namaTrim, $dimTrim . "'") || str_starts_with($namaTrim, $dimTrim . " ")) {
                    if (!str_contains($namaTrim, 'ACHIEVEMENT') && !str_contains($namaTrim, 'SCHEDULE')) {
                        $kunci = $nama;
                        break;
                    }
                }
            }
        }
    }
    if ($kunci === null) {
        $zip->close();
        throw new RuntimeException(
            'Sheet "' . $namaSheet . '" tidak ditemukan di file Target. Sheet yang tersedia: ' . implode(', ', $daftarSheet)
        );
    }

    $shared = xlsx_shared_strings($zip);
    $styleTgl = xlsx_style_tanggal($zip);
    $isiSheet = $zip->getFromName($sheets[$kunci]);
    $zip->close();
    if ($isiSheet === false || $isiSheet === '') {
        throw new RuntimeException('Isi sheet "' . $kunci . '" tidak dapat dibaca.');
    }

    $konversiSel = static function (string $tipe, string $valStr, int $sIdx) use ($shared, $styleTgl) {
        if ($tipe === 's') {
            $n = $valStr !== '' ? ($shared[(int)$valStr] ?? '') : null;
        } elseif ($tipe === 'str') {
            $n = $valStr;
        } elseif ($tipe === 'b') {
            $n = $valStr === '1' ? 1.0 : 0.0;
        } elseif ($tipe === 'e') {
            $n = null;
        } elseif ($tipe === 'd') {
            try {
                $n = $valStr !== '' ? new DateTimeImmutable($valStr) : null;
            } catch (Throwable $e) {
                $n = null;
            }
        } elseif ($valStr !== '' && is_numeric($valStr)) {
            $f = (float)$valStr;
            $n = (!empty($styleTgl[$sIdx])) ? xlsx_serial_ke_tanggal($f) : $f;
        } else {
            $n = null;
        }
        if (is_string($n) && in_array($n, NILAI_NA_PANDAS, true)) {
            return null;
        }
        return $n;
    };

    // Parser streaming XMLReader (jauh lebih ringan RAM & ~20x lebih cepat dibanding xpath per sel)
    if (class_exists('XMLReader')) {
        $xr = new XMLReader();
        if (@$xr->XML($isiSheet, null, LIBXML_NONET | LIBXML_COMPACT | LIBXML_PARSEHUGE)) {
            $baris = [];
            $inCell = false;
            $cellKIdx = 0;
            $cellRr = 0;
            $cellTipe = '';
            $cellSIdx = 0;
            $cellHasV = false;
            $cellVal = '';
            $cellInline = '';
            while (@$xr->read()) {
                $t = $xr->nodeType;
                if ($t === XMLReader::ELEMENT) {
                    $nm = $xr->localName;
                    if ($nm === 'row') {
                        $rAttr = $xr->getAttribute('r');
                        $curRowIdx = ($rAttr !== null && $rAttr !== '') ? ((int)$rAttr - 1) : count($baris);
                        if (!isset($baris[$curRowIdx])) {
                            $baris[$curRowIdx] = [];
                        }
                    } elseif ($nm === 'c') {
                        $ref = (string)($xr->getAttribute('r') ?? '');
                        if (preg_match('/^([A-Za-z]+)(\d+)$/', $ref, $mm)) {
                            $cellKIdx = xlsx_kolom_ke_indeks($mm[1]);
                            $cellRr = (int)$mm[2] - 1;
                            $cellTipe = (string)($xr->getAttribute('t') ?? '');
                            $cellSIdx = (int)($xr->getAttribute('s') ?? 0);
                            $cellHasV = false;
                            $cellVal = '';
                            $cellInline = '';
                            $inCell = !$xr->isEmptyElement;
                        } else {
                            $inCell = false;
                        }
                    } elseif ($inCell && $nm === 'v' && !$xr->isEmptyElement) {
                        $cellHasV = true;
                        $cellVal = $xr->readString();
                    } elseif ($inCell && $nm === 't' && $cellTipe === 'inlineStr' && !$xr->isEmptyElement) {
                        $cellInline .= $xr->readString();
                    }
                } elseif ($t === XMLReader::END_ELEMENT && $xr->localName === 'c' && $inCell) {
                    $inCell = false;
                    $nilai = null;
                    if ($cellTipe === 'inlineStr') {
                        $nilai = in_array($cellInline, NILAI_NA_PANDAS, true) ? null : $cellInline;
                    } elseif ($cellHasV) {
                        $nilai = $konversiSel($cellTipe, $cellVal, $cellSIdx);
                    }
                    if ($nilai !== null) {
                        $baris[$cellRr][$cellKIdx] = $nilai;
                    }
                }
            }
            $xr->close();
            unset($isiSheet);
            ksort($baris);
            return $baris;
        }
    }

    $xml = @simplexml_load_string($isiSheet, 'SimpleXMLElement', LIBXML_NONET | LIBXML_COMPACT | LIBXML_PARSEHUGE);
    unset($isiSheet);
    if ($xml === false || $xml === null) {
        throw new RuntimeException('Isi sheet "' . $kunci . '" tidak dapat dibaca.');
    }
    $xml->registerXPathNamespace('m', NS_SS);
    $baris = [];
    foreach ($xml->xpath('//m:sheetData/m:row') ?: [] as $row) {
        $row->registerXPathNamespace('m', NS_SS);
        $rIdx = isset($row['r']) ? ((int)$row['r'] - 1) : count($baris);
        foreach ($row->xpath('m:c') ?: [] as $c) {
            $ref = (string)$c['r'];
            if (!preg_match('/^([A-Za-z]+)(\d+)$/', $ref, $mm)) {
                continue;
            }
            $kIdx = xlsx_kolom_ke_indeks($mm[1]);
            $rr = (int)$mm[2] - 1;
            $tipe = (string)$c['t'];
            $nilai = null;
            if ($tipe === 'inlineStr') {
                $teks = '';
                foreach ($c->xpath('.//m:t') ?: [] as $t) {
                    $teks .= (string)$t;
                }
                $nilai = in_array($teks, NILAI_NA_PANDAS, true) ? null : $teks;
            } elseif (isset($c->v)) {
                $nilai = $konversiSel($tipe, (string)$c->v, (int)$c['s']);
            }
            if ($nilai !== null) {
                $baris[$rr][$kIdx] = $nilai;
            }
        }
        if (!isset($baris[$rIdx])) {
            $baris[$rIdx] = [];
        }
    }
    ksort($baris);
    return $baris;
}

/* ------------------------------------------------------------------------- */
/* DATA TARGET                                                                */
/* ------------------------------------------------------------------------- */

function parse_tanggal_join($val): ?DateTimeImmutable
{
    if ($val === null) {
        return null;
    }
    if ($val instanceof DateTimeInterface) {
        return new DateTimeImmutable($val->format('Y-m-d'));
    }
    $s = trim(py_str($val));
    if ($s === '' || in_array(u_lower($s), ['-', 'nan', 'none', 'vacant'], true)) {
        return null;
    }
    $c = preg_replace("/['’`]/u", ' ', u_lower($s));
    $c = preg_replace('/([0-9]+)([a-z]+)/', '$1 $2', (string)$c);
    $c = preg_replace('/([a-z]+)([0-9]+)/', '$1 $2', (string)$c);
    $tokens = preg_split('/\s+/', trim((string)$c), -1, PREG_SPLIT_NO_EMPTY) ?: [];
    if (count($tokens) >= 3 && ctype_digit($tokens[0]) && ctype_digit($tokens[2])) {
        $d = (int)$tokens[0];
        $m = PETA_BULAN_INDO[$tokens[1]] ?? 0;
        $y = (int)$tokens[2];
        if ($y < 100) {
            $y += 2000;
        }
        if ($m > 0 && checkdate($m, $d, $y)) {
            return new DateTimeImmutable(sprintf('%04d-%02d-%02d', $y, $m, $d));
        }
    }
    try {
        return new DateTimeImmutable((new DateTimeImmutable($s))->format('Y-m-d'));
    } catch (Throwable $e) {
        return null;
    }
}

function hitung_masa_kerja($valJoin, DateTimeImmutable $tglAcuan, string $namaAgen = ''): string
{
    if (strpos(u_upper($namaAgen), 'VACANT') !== false) {
        return '126 Tahun 10 Bulan';
    }
    $join = parse_tanggal_join($valJoin);
    if ($join === null) {
        return '-';
    }
    $awalBulan = new DateTimeImmutable($tglAcuan->format('Y-m-01'));
    if ($join >= $awalBulan) {
        return 'New Joiner';
    }
    $years = (int)$tglAcuan->format('Y') - (int)$join->format('Y');
    $months = (int)$tglAcuan->format('n') - (int)$join->format('n');
    if ((int)$tglAcuan->format('j') < (int)$join->format('j')) {
        $months--;
    }
    if ($months < 0) {
        $years--;
        $months += 12;
    }
    return $years . ' Tahun ' . $months . ' Bulan';
}

/**
 * Membaca Data Target (setara baca_data_target_excel Python).
 * @return list<array<string,mixed>>
 */
function baca_data_target(string $path, string $namaSheet, DateTimeImmutable $tglAcuan): array
{
    $sheets = null;
    $raw = xlsx_baca_sheet($path, $namaSheet, $sheets);
    $jumlahBaris = $raw ? (max(array_keys($raw)) + 1) : 0;

    $hasil = [];
    $sudahAda = [];
    $currTeam = '';
    $inBlock = false;
    $vacant = 0;

    for ($r = 11; $r < $jumlahBaris; $r++) {
        $row = $raw[$r] ?? [];
        $c0 = trim(py_str($row[0] ?? null));
        $c1 = $row[1] ?? null;
        $c2 = u_upper(trim(py_str($row[2] ?? null)));
        $c3 = trim(py_str($row[3] ?? null));
        $c4 = ke_angka($row[4] ?? null);
        $c5 = ke_angka($row[5] ?? null);
        $c8 = ke_angka($row[8] ?? null);

        if (u_upper($c0) === 'TEAM' && u_upper($c3) === 'NAMA') {
            $inBlock = true;
            $currTeam = '';
            continue;
        }
        if (!$inBlock) {
            continue;
        }
        if (u_upper($c0) === 'TOTAL' || u_upper($c3) === 'TOTAL' || strpos($c2, 'TARGET') !== false) {
            $inBlock = false;
            continue;
        }
        if ($c0 !== '' && !in_array(u_upper($c0), ['NAN', 'TEAM', 'TOTAL'], true)) {
            $currTeam = rapatkan_spasi(u_upper($c0));
        }
        if ($c3 === '' || in_array(u_upper($c3), ['NAN', 'NAMA', 'REGULER', 'TOTAL'], true)) {
            continue;
        }
        if ($c4 === null && $c5 === null) {
            continue;
        }

        $reg = $c4 !== null ? (int)round($c4) : 0;
        $yr = $c5 !== null ? (int)round($c5) : 0;

        // Penyelarasan Target Reguler Probation sesuai standar laporan perusahaan
        if ($c2 === 'PROBATION III' && $reg === 33) {
            $reg = 38;
        } elseif ($c2 === 'PROBATION II' && $reg === 23) {
            $reg = strpos(u_upper($c3), 'DENSON') !== false ? 32 : 33;
        }

        $targetAll = $reg + $yr;
        $dailyPaid = $c8 !== null ? (int)round($c8) : ($targetAll >= 55 ? 3 : 2);

        $namaClean = normalisasi_nama_agen($c3);
        $ldrDefault = TEAM_EXCEL_KE_LEADER[$currTeam] ?? u_title($currTeam);
        if ($currTeam === 'TOMMY') {
            $ldrDefault = in_array($namaClean, AGEN_TOMMY_KE_FIRLY, true) ? 'Firliansyah' : 'Yudha Irawan';
        }

        if ($namaClean === 'VACANT') {
            $vacant++;
            $keyAgent = 'VACANT__' . $ldrDefault . '__' . $vacant;
            $tampil = 'Vacant';
        } else {
            $keyAgent = $namaClean;
            $tampil = u_title(rapatkan_spasi(hapus_zero_width($c3)));
        }

        if (isset($sudahAda[$keyAgent])) {
            continue; // drop_duplicates(keep='first')
        }
        $sudahAda[$keyAgent] = true;

        $hasil[] = [
            'Agent_Key' => $keyAgent,
            'Nama_Tampil' => $tampil,
            'Leader_Default' => $ldrDefault,
            'Masa Kerja' => hitung_masa_kerja($c1, $tglAcuan, $namaClean),
            'Level' => $c2 !== '' ? $c2 : '-',
            'Target Reguler' => $reg,
            'Target Yearly' => $yr,
            'TARGET ALL' => $targetAll,
            'Daily Paid Normal' => $dailyPaid,
        ];
    }
    return $hasil;
}

/* ------------------------------------------------------------------------- */
/* DATA PROSPECT (.xls HTML / .xlsx)                                           */
/* ------------------------------------------------------------------------- */

/** Mengubah teks tanggal sistem menjadi integer YYYYMMDD (atau null). */
function tanggal_ke_int($v): ?int
{
    if ($v === null) {
        return null;
    }
    if ($v instanceof DateTimeInterface) {
        return (int)$v->format('Ymd');
    }
    $s = trim((string)$v);
    if ($s === '' || $s === '-') {
        return null;
    }
    if (preg_match('/^(\d{4})-(\d{1,2})-(\d{1,2})/', $s, $m) && checkdate((int)$m[2], (int)$m[3], (int)$m[1])) {
        return (int)sprintf('%04d%02d%02d', $m[1], $m[2], $m[3]);
    }
    if (preg_match('/^(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{4})/', $s, $m) && checkdate((int)$m[2], (int)$m[1], (int)$m[3])) {
        return (int)sprintf('%04d%02d%02d', $m[3], $m[2], $m[1]);
    }
    return null;
}

function bersihkan_sel_html(string $html): string
{
    $t = strip_tags($html);
    $t = html_entity_decode($t, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $t = str_replace("\xC2\xA0", ' ', $t);
    return trim($t);
}

/**
 * Membaca tabel pertama dari file HTML (.xls dari sistem) -> [header[], rows[][]].
 * @return array{0:list<string>,1:list<list<string>>}
 */
function baca_tabel_html(string $path): array
{
    $html = @file_get_contents($path);
    if ($html === false || $html === '') {
        throw new RuntimeException('File prospect kosong atau tidak dapat dibaca.');
    }
    if (function_exists('mb_check_encoding') && !mb_check_encoding($html, 'UTF-8')) {
        $html = mb_convert_encoding($html, 'UTF-8', 'Windows-1252');
    }
    $header = null;
    $rows = [];
    $lenHtml = strlen($html);
    $offset = 0;
    while ($offset < $lenHtml) {
        $posStart = stripos($html, '<tr', $offset);
        if ($posStart === false) {
            break;
        }
        $posEnd = stripos($html, '</tr>', $posStart);
        if ($posEnd === false) {
            $posEnd = $lenHtml;
        }
        $isi = substr($html, $posStart, $posEnd - $posStart);
        $offset = $posEnd + 5;
        if (!preg_match_all('#<t[dh]\b[^>]*>(.*?)</t[dh]>#is', $isi, $mm)) {
            continue;
        }
        $sel = array_map('bersihkan_sel_html', $mm[1]);
        if ($header === null) {
            $header = array_map('trim', $sel);
        } else {
            $rows[] = $sel;
        }
    }
    unset($html);
    if ($header === null) {
        throw new RuntimeException('Tabel data tidak ditemukan di file prospect (format file tidak dikenali).');
    }
    return [$header, $rows];
}

/**
 * Membaca file CSV / TSV dengan deteksi delimiter otomatis (, ; \t).
 * @return array{0:list<string>,1:list<list<string>>}
 */
function baca_tabel_csv(string $path): array
{
    $fh = @fopen($path, 'rb');
    if ($fh === false) {
        throw new RuntimeException('File CSV prospect tidak dapat dibaca.');
    }
    $barisPertama = (string)fgets($fh);
    rewind($fh);
    $kandidat = [',', ';', "\t"];
    $delim = ',';
    $maks = -1;
    foreach ($kandidat as $d) {
        $cnt = substr_count($barisPertama, $d);
        if ($cnt > $maks) {
            $maks = $cnt;
            $delim = $d;
        }
    }
    $header = null;
    $rows = [];
    while (($cols = fgetcsv($fh, 0, $delim)) !== false) {
        if ($cols === [null] || $cols === []) {
            continue;
        }
        if ($header === null) {
            $header = array_map(function ($v) {
                $s = (string)$v;
                if (str_starts_with($s, "\xEF\xBB\xBF")) {
                    $s = substr($s, 3);
                }
                return trim($s);
            }, $cols);
        } else {
            $rows[] = array_map(fn($v) => trim((string)$v), $cols);
        }
    }
    fclose($fh);
    if ($header === null || !$header) {
        throw new RuntimeException('Header CSV prospect kosong atau tidak valid.');
    }
    return [$header, $rows];
}

/** Mendeteksi jenis file dari isi: 'xlsx' | 'html' | 'csv' | 'xls_biner' | 'tidak_dikenal'. */
function deteksi_jenis_file(string $path): string
{
    $fh = @fopen($path, 'rb');
    if ($fh === false) {
        return 'tidak_dikenal';
    }
    $awal = (string)fread($fh, 2048);
    fclose($fh);
    if (substr($awal, 0, 2) === 'PK') {
        return 'xlsx';
    }
    if (substr($awal, 0, 4) === "\xD0\xCF\x11\xE0") {
        return 'xls_biner';
    }
    if (stripos($awal, '<table') !== false || stripos($awal, '<html') !== false || stripos($awal, '<tr') !== false) {
        return 'html';
    }
    if (
        stripos($awal, 'salesname') !== false ||
        stripos($awal, 'sales leader') !== false ||
        stripos($awal, 'active date') !== false
    ) {
        return 'csv';
    }
    return 'tidak_dikenal';
}

/**
 * Membaca satu file prospect -> daftar baris ringkas.
 * Setiap baris: [leader, salesname, tipe, harga, created, active, payment, statusPay, kunciDedup]
 * @return array{rows:list<array>, ada_payment:bool, ada_created:bool, ada_status:bool}
 */
function baca_file_prospect(string $path, string $namaTampil): array
{
    $jenis = deteksi_jenis_file($path);
    if ($jenis === 'xls_biner') {
        throw new RuntimeException('File "' . $namaTampil . '" berformat Excel biner (.xls lama). Buka di Excel lalu "Save As" .xlsx, atau gunakan file .xls asli dari sistem (format HTML).');
    }
    if ($jenis === 'xlsx') {
        $sheets = null;
        $zip = xlsx_buka($path);
        $daftar = xlsx_daftar_sheet($zip);
        $zip->close();
        $pertama = array_key_first($daftar);
        if ($pertama === null) {
            throw new RuntimeException('File "' . $namaTampil . '" tidak memiliki sheet.');
        }
        $raw = xlsx_baca_sheet($path, $pertama, $sheets);
        if (!$raw) {
            throw new RuntimeException('File "' . $namaTampil . '" kosong.');
        }
        $idxBaris = array_keys($raw);
        $hdrRow = $raw[$idxBaris[0]];
        $maxKol = $hdrRow ? max(array_keys($hdrRow)) : -1;
        $header = [];
        for ($k = 0; $k <= $maxKol; $k++) {
            $header[$k] = trim(py_str($hdrRow[$k] ?? null));
        }
        $rows = [];
        for ($i = 1; $i < count($idxBaris); $i++) {
            $r = $raw[$idxBaris[$i]];
            $line = [];
            for ($k = 0; $k <= $maxKol; $k++) {
                $v = $r[$k] ?? null;
                $line[$k] = $v instanceof DateTimeInterface ? $v->format('Y-m-d H:i:s') : py_str($v);
            }
            $rows[] = $line;
        }
    } elseif ($jenis === 'html') {
        [$header, $rows] = baca_tabel_html($path);
    } elseif ($jenis === 'csv') {
        [$header, $rows] = baca_tabel_csv($path);
    } else {
        throw new RuntimeException('File "' . $namaTampil . '" tidak dikenali. Gunakan file .xls (HTML), .xlsx, atau .csv dari sistem.');
    }

    $peta = [];
    foreach ($header as $i => $h) {
        $hClean = preg_replace('/^\xEF\xBB\xBF/', '', $h) ?? $h;
        $peta[u_lower(trim($hClean))] = $i;
    }
    foreach (['salesname', 'sales leader', 'active date'] as $wajib) {
        if (!isset($peta[$wajib])) {
            throw new RuntimeException('File "' . $namaTampil . '" tidak memiliki kolom wajib "' . $wajib . '". Pastikan ini file list prospect dari sistem.');
        }
    }
    $iPno = $peta['prospect no'] ?? null;
    $iCno = $peta['customer no'] ?? null;
    $iCname = $peta['customer name'] ?? ($peta['full name'] ?? null);
    $iLdr = $peta['sales leader'];
    $iSls = $peta['salesname'];
    $iTipe = $peta['tipe paket'] ?? null;
    $iHarga = $peta['service price'] ?? null;
    $iCreated = $peta['created date'] ?? null;
    $iInst = $peta['instalasi date'] ?? null;
    $iActive = $peta['active date'];
    $iPay = $peta['payment date'] ?? null;
    $iStatus = $peta['status payment'] ?? null;
    $iStatWo = $peta['status'] ?? null;

    $hasil = [];
    foreach ($rows as $r) {
        $get = function (?int $i) use ($r) {
            if ($i === null || !isset($r[$i])) {
                return null;
            }
            $v = $r[$i];
            return in_array($v, NILAI_NA_PANDAS, true) ? null : $v;
        };
        $active = tanggal_ke_int($get($iActive));
        $created = $iCreated === null ? $active : tanggal_ke_int($get($iCreated));
        $payment = $iPay === null ? $active : tanggal_ke_int($get($iPay));
        $instalasi = $iInst === null ? null : tanggal_ke_int($get($iInst));
        $statusWo = $iStatWo === null ? '' : trim((string)($get($iStatWo) ?? ''));
        $harga = ke_angka($get($iHarga));

        $pnoVal = trim((string)($get($iPno) ?? ''));
        $cnoVal = trim((string)($get($iCno) ?? ''));
        $cnameRaw = trim((string)($get($iCname) ?? ''));
        $cnameVal = u_upper(rapatkan_spasi($cnameRaw));
        $hasCust = ($iCname === null) ? true : ($cnameRaw !== '');
        $idKey = ($pnoVal !== '' && $cnameVal !== '')
            ? ('PK2:' . $pnoVal . '|' . $cnameVal)
            : (($pnoVal !== '' && $cnoVal !== '')
                ? ('PKC:' . $pnoVal . '|' . $cnoVal)
                : ('MD5:' . md5(implode("\x1f", $r))));

        $hasil[] = [
            normalisasi_nama_leader($get($iLdr)),
            $get($iSls),
            $get($iTipe) !== null ? trim((string)$get($iTipe)) : '',
            $harga ?? 0.0,
            $created,
            $active,
            $payment,
            $iStatus === null ? null : $get($iStatus),
            $idKey,
            $instalasi,
            $statusWo,
            $hasCust,
        ];
    }
    return ['rows' => $hasil, 'ada_payment' => $iPay !== null, 'ada_created' => $iCreated !== null, 'ada_status' => $iStatus !== null];
}

/**
 * Menormalkan primary key prospect dari format lama PK:pno|cno|cname ke PK2:pno|cname
 * agar baris yg Customer No-nya baru terisi saat pembayaran tidak menjadi duplikat.
 */
function normalisasi_pk_prospect(string $rawKey): string
{
    if (str_starts_with($rawKey, 'PK2:') || str_starts_with($rawKey, 'PKC:') || str_starts_with($rawKey, 'MD5:')) {
        return $rawKey;
    }
    if (str_starts_with($rawKey, 'PK:')) {
        $parts = explode('|', substr($rawKey, 3), 3);
        if (count($parts) === 3) {
            $pno = trim($parts[0]);
            $cno = trim($parts[1]);
            $cname = u_upper(rapatkan_spasi(trim($parts[2])));
            if ($pno !== '' && $cname !== '') {
                return 'PK2:' . $pno . '|' . $cname;
            }
            if ($pno !== '' && $cno !== '') {
                return 'PKC:' . $pno . '|' . $cno;
            }
        }
    }
    return $rawKey;
}

/** Skor kelengkapan status baris untuk memilih versi terbaru saat deduplikasi pool lama. */
function skor_kelengkapan_row(array $row): int
{
    $score = 0;
    if (isset($row[5]) && $row[5] !== null && $row[5] !== '') {
        $score += 4;
    }
    if (u_upper(trim((string)($row[7] ?? ''))) === 'PAID') {
        $score += 2;
    }
    if (isset($row[6]) && $row[6] !== null && $row[6] !== '') {
        $score += 1;
    }
    return $score;
}

/** Menggabungkan & membersihkan duplikat dari pool prospect yang sudah tersimpan di server. */
function deduplikasi_pool_rows(array $rows): array
{
    $byKey = [];
    foreach ($rows as $row) {
        if (!is_array($row) || !isset($row[8])) {
            continue;
        }
        $normKey = normalisasi_pk_prospect((string)$row[8]);
        $row[8] = $normKey;
        if (!isset($byKey[$normKey]) || skor_kelengkapan_row($row) >= skor_kelengkapan_row($byKey[$normKey])) {
            $byKey[$normKey] = $row;
        }
    }
    return $byKey;
}

/** Mendeteksi bulan (YYYYMM) yang dimuat secara utuh oleh sebuah file upload prospect. */
function deteksi_bulan_penuh_rows(array $rows, int $minRowsPerMonth = 50): array
{
    $counts = [];
    foreach ($rows as $row) {
        $cr = isset($row[4]) && $row[4] !== null ? (int)$row[4] : 0;
        if ($cr >= 20000101) {
            $ym = intdiv($cr, 100);
            $counts[$ym] = ($counts[$ym] ?? 0) + 1;
        }
    }
    $full = [];
    foreach ($counts as $ym => $cnt) {
        if ($cnt >= $minRowsPerMonth) {
            $full[$ym] = true;
        }
    }
    return $full;
}

/* ------------------------------------------------------------------------- */
/* FILTER MTD & HARIAN (SO, PAID, SA, JUMLAH AGENT BLM PRODUKTIF)            */
/* ------------------------------------------------------------------------- */

/** Indeks kolom di baris ringkas */
const P_LDR = 0;
const P_SLS = 1;
const P_TIPE = 2;
const P_HARGA = 3;
const P_CREATED = 4;
const P_ACTIVE = 5;
const P_PAYMENT = 6;
const P_STATUS = 7;
const P_INSTALASI = 9;
const P_STATUS_WO = 10;
const P_HAS_CUST = 11;

/**
 * @param list<array> $rows
 * @return list<array>
 */
function filter_mtd(array $rows, int $kolTgl, int $bulan, int $tahun, int $hari, bool $fallbackMinDay, ?bool $wajibPaid): array
{
    $bulanIni = [];
    foreach ($rows as $r) {
        $t = $r[$kolTgl];
        if ($t === null || intdiv($t, 10000) !== $tahun || intdiv($t % 10000, 100) !== $bulan) {
            continue;
        }
        if ($wajibPaid === true && u_upper(trim((string)($r[P_STATUS] ?? ''))) !== 'PAID') {
            continue;
        }
        $bulanIni[] = $r;
    }
    if (!$bulanIni) {
        return [];
    }
    $mtd = array_values(array_filter($bulanIni, fn($r) => ($r[$kolTgl] % 100) <= $hari));
    if (!$mtd && $fallbackMinDay) {
        $minDay = min(array_map(fn($r) => $r[$kolTgl] % 100, $bulanIni));
        $batas = $minDay + $hari - 1;
        $mtd = array_values(array_filter($bulanIni, fn($r) => ($r[$kolTgl] % 100) <= $batas));
    }
    return $mtd;
}

/**
 * Mengembalikan daftar tanggal (hari 1..31) yang tersedia di bulan/tahun tertentu.
 * @param list<array> $prospect
 * @return list<int>
 */
function daftar_hari_tersedia_bulan(array $prospect, int $bulan, int $tahun, int $sertakanHari = 0): array
{
    $set = [];
    foreach ($prospect as $r) {
        foreach ([P_CREATED, P_PAYMENT, P_ACTIVE] as $idxT) {
            $t = $r[$idxT] ?? null;
            if ($t !== null && intdiv((int)$t, 10000) === $tahun && intdiv(((int)$t) % 10000, 100) === $bulan) {
                $set[((int)$t) % 100] = true;
            }
        }
    }
    if ($sertakanHari >= 1 && $sertakanHari <= 31) {
        $set[$sertakanHari] = true;
    }
    $hariList = array_keys($set);
    sort($hariList, SORT_NUMERIC);
    return $hariList;
}

/**
 * Menghitung Tabel Rekap Harian ({tgl}: SO, PAID, SA) & Jumlah Agent Belum Produktif (SO, PAID, SA) per Leader.
 * @param list<array> $prospect
 * @param list<array<string,mixed>> $target
 * @return array{date_label:string,day:int,rows:list<array<string,mixed>>}
 */
function hitung_rekap_harian_blm_produktif(array $prospect, array $target, int $bulan, int $tahun, int $hariHarian): array
{
    $hariDlmBulan = cal_days_in_month_aman($bulan, $tahun);
    $hariValid = max(1, min($hariHarian, $hariDlmBulan));
    $tglInt = ($tahun * 10000) + ($bulan * 100) + $hariValid;
    $namaBln = NAMA_BULAN_TAMPIL[$bulan] ?? 'Nov';
    $dateLabel = sprintf('%d-%s-%02d', $hariValid, $namaBln, $tahun % 100);

    $soLdr = [];
    $paidLdr = [];
    $saLdr = [];
    $soAgen = [];
    $paidAgen = [];
    $saAgen = [];

    foreach ($prospect as $r) {
        $ldr = trim((string)($r[P_LDR] ?? ''));
        $agKey = normalisasi_nama_agen($r[P_SLS] ?? '');
        $validAg = !in_array($agKey, ['', 'NAN', 'NONE', 'TOTAL', '-'], true);
        if (!$validAg) {
            continue;
        }

        if (($r[P_CREATED] ?? null) === $tglInt) {
            if ($ldr !== '') {
                $soLdr[$ldr] = ($soLdr[$ldr] ?? 0) + 1;
            }
            $soAgen[$agKey] = ($soAgen[$agKey] ?? 0) + 1;
        }

        $isPaid = u_upper(trim((string)($r[P_STATUS] ?? ''))) === 'PAID';
        if ($isPaid && ($r[P_PAYMENT] ?? null) === $tglInt) {
            if ($ldr !== '') {
                $paidLdr[$ldr] = ($paidLdr[$ldr] ?? 0) + 1;
            }
            $paidAgen[$agKey] = ($paidAgen[$agKey] ?? 0) + 1;
        }

        if (($r[P_ACTIVE] ?? null) === $tglInt) {
            if ($ldr !== '') {
                $saLdr[$ldr] = ($saLdr[$ldr] ?? 0) + 1;
            }
            $saAgen[$agKey] = ($saAgen[$agKey] ?? 0) + 1;
        }
    }

    // Kelompokkan seluruh slot tim (termasuk slot Vacant) per Leader dari sheet Target
    $agenPerLdr = [];
    foreach ($target as $t) {
        $k = (string)($t['Agent_Key'] ?? '');
        if ($k === '') {
            continue;
        }
        $ldr = trim((string)($t['Leader_Default'] ?? ''));
        if ($ldr === '') {
            continue;
        }
        $agenPerLdr[$ldr][] = [
            'key' => $k,
            'name' => trim((string)($t['Nama_Tampil'] ?? $k)),
        ];
    }

    $semuaLdrSet = [];
    foreach (array_keys($agenPerLdr) as $l) {
        $semuaLdrSet[$l] = true;
    }
    foreach ([$soLdr, $paidLdr, $saLdr] as $mapL) {
        foreach ($mapL as $l => $v) {
            if ($v > 0) {
                $semuaLdrSet[$l] = true;
            }
        }
    }

    $rows = [];
    foreach (array_keys($semuaLdrSet) as $ldr) {
        $soVal = (int)($soLdr[$ldr] ?? 0);
        $paidVal = (int)($paidLdr[$ldr] ?? 0);
        $saVal = (int)($saLdr[$ldr] ?? 0);

        $daftarAg = $agenPerLdr[$ldr] ?? [];
        $listBlmSo = [];
        $listBlmPaid = [];
        $listBlmSa = [];
        foreach ($daftarAg as $ag) {
            $ak = $ag['key'];
            if ((int)($soAgen[$ak] ?? 0) === 0) {
                $listBlmSo[] = $ag['name'];
            }
            if ((int)($paidAgen[$ak] ?? 0) === 0) {
                $listBlmPaid[] = $ag['name'];
            }
            if ((int)($saAgen[$ak] ?? 0) === 0) {
                $listBlmSa[] = $ag['name'];
            }
        }

        $rows[] = [
            'leader' => $ldr,
            'so' => $soVal,
            'paid' => $paidVal,
            'sa' => $saVal,
            'blm_so' => count($listBlmSo),
            'blm_paid' => count($listBlmPaid),
            'blm_sa' => count($listBlmSa),
            'total_agents' => count($daftarAg),
            'agents_blm_so' => $listBlmSo,
            'agents_blm_paid' => $listBlmPaid,
            'agents_blm_sa' => $listBlmSa,
            'is_grand_total' => false,
        ];
    }

    // Urutkan descending SO, lalu PAID, lalu SA (persis seperti tabel gambar perusahaan)
    usort($rows, function ($x, $y) {
        return [$y['so'], $y['paid'], $y['sa'], $x['leader']]
            <=> [$x['so'], $x['paid'], $x['sa'], $y['leader']];
    });

    $rows[] = [
        'leader' => 'Grand Total',
        'so' => array_sum(array_column($rows, 'so')),
        'paid' => array_sum(array_column($rows, 'paid')),
        'sa' => array_sum(array_column($rows, 'sa')),
        'blm_so' => array_sum(array_column($rows, 'blm_so')),
        'blm_paid' => array_sum(array_column($rows, 'blm_paid')),
        'blm_sa' => array_sum(array_column($rows, 'blm_sa')),
        'total_agents' => array_sum(array_column($rows, 'total_agents')),
        'agents_blm_so' => [],
        'agents_blm_paid' => [],
        'agents_blm_sa' => [],
        'is_grand_total' => true,
    ];

    return [
        'date_label' => $dateLabel,
        'day' => $hariValid,
        'rows' => $rows,
    ];
}

/* ------------------------------------------------------------------------- */
/* MONITORING WORK ORDER (WO TODAY | WAITING WO | WO BESOK)                  */
/* ------------------------------------------------------------------------- */

/**
 * Mengembalikan daftar tanggal (hari 1..31) yang memiliki jadwal Instalasi Date di bulan aktif.
 * @param list<array> $prospect
 * @return list<int>
 */
function daftar_hari_wo_tersedia(array $prospect, int $bulan, int $tahun, int $sertakanHari = 0): array
{
    $set = [];
    foreach ($prospect as $r) {
        $t = $r[P_INSTALASI] ?? null;
        if ($t !== null && intdiv((int)$t, 10000) === $tahun && intdiv(((int)$t) % 10000, 100) === $bulan) {
            $set[((int)$t) % 100] = true;
        }
    }
    if ($sertakanHari >= 1 && $sertakanHari <= 31) {
        $set[$sertakanHari] = true;
    }
    $hariList = array_keys($set);
    sort($hariList, SORT_NUMERIC);
    return $hariList;
}

/**
 * Menyusun baris Pivot Excel 1-kolom (Sales Leader -> Salesname -> Leader Total -> Grand Total).
 * @param array<string,array<string,int>> $byLdrAgent
 * @return array{rows:list<array<string,mixed>>,grand_total:int}
 */
function susun_pivot_wo_1kolom(array $byLdrAgent): array
{
    $leaders = array_keys($byLdrAgent);
    usort($leaders, 'strnatcasecmp');
    $rows = [];
    $grand = 0;
    foreach ($leaders as $ldr) {
        $agenMap = $byLdrAgent[$ldr];
        $agenNames = array_keys($agenMap);
        usort($agenNames, 'strnatcasecmp');
        $sub = 0;
        foreach ($agenNames as $sn) {
            $cnt = (int)$agenMap[$sn];
            $sub += $cnt;
            $rows[] = [
                'leader' => $ldr,
                'salesname' => $sn,
                'total' => $cnt,
                'row_type' => 'agent',
            ];
        }
        $grand += $sub;
        $rows[] = [
            'leader' => $ldr,
            'salesname' => $ldr . ' Total',
            'total' => $sub,
            'row_type' => 'leader_total',
        ];
    }
    if ($rows) {
        $rows[] = [
            'leader' => 'Grand Total',
            'salesname' => 'Grand Total',
            'total' => $grand,
            'row_type' => 'grand_total',
        ];
    }
    return ['rows' => $rows, 'grand_total' => $grand];
}

/**
 * Menghitung 3 Tabel Work Order sesuai Pivot Excel perusahaan:
 *   1. WO TODAY  (Instalasi Date = hariWo, Status = ALL -> termasuk Active/SA, On Installation, Propose To Cancel, READY, Refund, Reschedule, Waiting WO)
 *   2. WO BESOK  (Instalasi Date > hariWo / Multiple Items terjadwal berikutnya, Status = ALL)
 *   3. WAITING WO (Instalasi Date = blank, Status in Back To Sales / READY / Reschedule / Waiting WO pada bulan aktif + bulan lalu)
 * @param list<array> $prospect
 * @return array<string,mixed>
 */
function hitung_wo_laporan(array $prospect, int $bulan, int $tahun, int $hariWo): array
{
    $hariDlmBulan = cal_days_in_month_aman($bulan, $tahun);
    $hariValid = max(1, min($hariWo, $hariDlmBulan));
    $dtToday = new DateTimeImmutable(sprintf('%04d-%02d-%02d', $tahun, $bulan, $hariValid));
    $dtBesok = $dtToday->modify('+1 day');

    $tglTodayInt = (int)$dtToday->format('Ymd');
    $tglBesokInt = (int)$dtBesok->format('Ymd');
    $blnTahunAktif = ($tahun * 100) + $bulan;
    $blnTahunLalu = ($bulan === 1) ? (($tahun - 1) * 100 + 12) : (($tahun * 100) + ($bulan - 1));

    $todayLabel = (int)$dtToday->format('j') . '-' . (NAMA_BULAN_TAMPIL[(int)$dtToday->format('n')] ?? 'Nov') . '-' . substr($dtToday->format('Y'), -2);
    $besokLabel = (int)$dtBesok->format('j') . '-' . (NAMA_BULAN_TAMPIL[(int)$dtBesok->format('n')] ?? 'Nov') . '-' . substr($dtBesok->format('Y'), -2);

    $todayByLdrAgent = [];
    $todayColSet = [];
    $todayStatusTotals = [];
    $waitingByLdrAgent = [];
    $waitingBreakdown = [
        'Back To Sales' => 0,
        'READY' => 0,
        'Reschedule' => 0,
        'Waiting WO' => 0,
    ];
    $besokByLdrAgent = [];
    $besokH1Total = 0;
    $besokLaterTotal = 0;
    $summaryLdr = [];
    $summaryAgent = [];

    $emptyCounters = static function (): array {
        return [
            'today_sa' => 0,
            'today_on_installation' => 0,
            'today_reschedule' => 0,
            'today_waiting_wo' => 0,
            'today_refund' => 0,
            'today_other' => 0,
            'today_total' => 0,
            'wo_besok' => 0,
            'waiting_wo' => 0,
        ];
    };

    foreach ($prospect as $r) {
        $hasCust = isset($r[P_HAS_CUST]) ? (bool)$r[P_HAS_CUST] : true;
        if (!$hasCust) {
            continue;
        }
        $ldr = trim((string)($r[P_LDR] ?? ''));
        if ($ldr === '') {
            $ldr = '(blank)';
        }
        $snRaw = trim((string)($r[P_SLS] ?? ''));
        $sn = ($snRaw === '' || in_array(u_upper($snRaw), ['NAN', 'NONE', '-'], true)) ? '(blank)' : $snRaw;

        $instInt = isset($r[P_INSTALASI]) && $r[P_INSTALASI] !== null ? (int)$r[P_INSTALASI] : null;
        $crInt = isset($r[P_CREATED]) && $r[P_CREATED] !== null ? (int)$r[P_CREATED] : null;
        $stRaw = trim((string)($r[P_STATUS_WO] ?? ''));
        $stLow = u_lower($stRaw);

        $ensureSummary = static function () use (&$summaryLdr, &$summaryAgent, $ldr, $sn, $emptyCounters): void {
            if (!isset($summaryLdr[$ldr])) {
                $summaryLdr[$ldr] = array_merge(['leader' => $ldr], $emptyCounters());
            }
            if (!isset($summaryAgent[$ldr][$sn])) {
                $summaryAgent[$ldr][$sn] = array_merge(['leader' => $ldr, 'salesname' => $sn], $emptyCounters());
            }
        };

        // 1. WO TODAY (Instalasi Date == Today, Status = ALL -> termasuk Active sebagai SA!)
        if ($instInt === $tglTodayInt) {
            $stCol = $stRaw !== '' ? $stRaw : '(blank)';
            $todayColSet[$stCol] = true;
            $todayStatusTotals[$stCol] = ($todayStatusTotals[$stCol] ?? 0) + 1;

            if (!isset($todayByLdrAgent[$ldr][$sn])) {
                $todayByLdrAgent[$ldr][$sn] = array_merge($emptyCounters(), ['statuses' => []]);
            }
            $todayByLdrAgent[$ldr][$sn]['statuses'][$stCol] = ($todayByLdrAgent[$ldr][$sn]['statuses'][$stCol] ?? 0) + 1;
            $todayByLdrAgent[$ldr][$sn]['today_total']++;

            $ensureSummary();
            $summaryLdr[$ldr]['today_total']++;
            $summaryAgent[$ldr][$sn]['today_total']++;

            if ($stLow === 'active') {
                $todayByLdrAgent[$ldr][$sn]['today_sa']++;
                $summaryLdr[$ldr]['today_sa']++;
                $summaryAgent[$ldr][$sn]['today_sa']++;
            } elseif ($stLow === 'on installation') {
                $todayByLdrAgent[$ldr][$sn]['today_on_installation']++;
                $summaryLdr[$ldr]['today_on_installation']++;
                $summaryAgent[$ldr][$sn]['today_on_installation']++;
            } elseif ($stLow === 'reschedule') {
                $todayByLdrAgent[$ldr][$sn]['today_reschedule']++;
                $summaryLdr[$ldr]['today_reschedule']++;
                $summaryAgent[$ldr][$sn]['today_reschedule']++;
            } elseif ($stLow === 'waiting wo') {
                $todayByLdrAgent[$ldr][$sn]['today_waiting_wo']++;
                $summaryLdr[$ldr]['today_waiting_wo']++;
                $summaryAgent[$ldr][$sn]['today_waiting_wo']++;
            } else {
                if ($stLow === 'refund') {
                    $todayByLdrAgent[$ldr][$sn]['today_refund']++;
                    $summaryLdr[$ldr]['today_refund']++;
                    $summaryAgent[$ldr][$sn]['today_refund']++;
                }
                $todayByLdrAgent[$ldr][$sn]['today_other']++;
                $summaryLdr[$ldr]['today_other']++;
                $summaryAgent[$ldr][$sn]['today_other']++;
            }
        }

        // 2. WO BESOK (Instalasi Date > Today / Multiple Items terjadwal masa depan, Status = ALL)
        if ($instInt !== null && $instInt > $tglTodayInt) {
            $besokByLdrAgent[$ldr][$sn] = ($besokByLdrAgent[$ldr][$sn] ?? 0) + 1;
            if ($instInt === $tglBesokInt) {
                $besokH1Total++;
            } else {
                $besokLaterTotal++;
            }
            $ensureSummary();
            $summaryLdr[$ldr]['wo_besok']++;
            $summaryAgent[$ldr][$sn]['wo_besok']++;
        }

        // 3. WAITING WO (Instalasi Date == blank & Status in Back To Sales | READY | Reschedule | Waiting WO)
        if ($instInt === null && in_array($stLow, ['back to sales', 'ready', 'reschedule', 'waiting wo'], true)) {
            $crYm = $crInt !== null ? intdiv($crInt, 100) : null;
            if ($crYm === null || ($crYm >= $blnTahunLalu && $crYm <= $blnTahunAktif)) {
                $waitingByLdrAgent[$ldr][$sn] = ($waitingByLdrAgent[$ldr][$sn] ?? 0) + 1;
                if ($stLow === 'back to sales') {
                    $waitingBreakdown['Back To Sales']++;
                } elseif ($stLow === 'ready') {
                    $waitingBreakdown['READY']++;
                } elseif ($stLow === 'reschedule') {
                    $waitingBreakdown['Reschedule']++;
                } else {
                    $waitingBreakdown['Waiting WO']++;
                }
                $ensureSummary();
                $summaryLdr[$ldr]['waiting_wo']++;
                $summaryAgent[$ldr][$sn]['waiting_wo']++;
            }
        }
    }

    // Urutkan kolom status WO TODAY alfabetis persis Pivot Excel
    $todayCols = array_keys($todayColSet);
    usort($todayCols, 'strnatcasecmp');
    ksort($todayStatusTotals, SORT_NATURAL | SORT_FLAG_CASE);

    // Susun Pivot WO TODAY (kolom dinamis sesuai status yang muncul + SA + Grand Total)
    $todayLeaders = array_keys($todayByLdrAgent);
    usort($todayLeaders, 'strnatcasecmp');
    $todayRows = [];
    $gtSa = 0;
    $gtOn = 0;
    $gtResch = 0;
    $gtWait = 0;
    $gtRef = 0;
    $gtOther = 0;
    $gtTot = 0;
    $gtStatuses = array_fill_keys($todayCols, 0);

    foreach ($todayLeaders as $ldr) {
        $agenMap = $todayByLdrAgent[$ldr];
        $agenNames = array_keys($agenMap);
        usort($agenNames, 'strnatcasecmp');
        $subSa = 0;
        $subOn = 0;
        $subResch = 0;
        $subWait = 0;
        $subRef = 0;
        $subOther = 0;
        $subTot = 0;
        $subStatuses = array_fill_keys($todayCols, 0);

        foreach ($agenNames as $sn) {
            $c = $agenMap[$sn];
            $subSa += $c['today_sa'];
            $subOn += $c['today_on_installation'];
            $subResch += $c['today_reschedule'];
            $subWait += $c['today_waiting_wo'];
            $subRef += $c['today_refund'];
            $subOther += $c['today_other'];
            $subTot += $c['today_total'];
            $stMapRow = [];
            foreach ($todayCols as $colNm) {
                $valC = (int)($c['statuses'][$colNm] ?? 0);
                $stMapRow[$colNm] = $valC;
                $subStatuses[$colNm] += $valC;
            }
            $todayRows[] = [
                'leader' => $ldr,
                'salesname' => $sn,
                'sa' => $c['today_sa'],
                'on_installation' => $c['today_on_installation'],
                'reschedule' => $c['today_reschedule'],
                'refund' => $c['today_refund'],
                'waiting_wo' => $c['today_waiting_wo'],
                'other' => $c['today_other'],
                'total' => $c['today_total'],
                'statuses' => $stMapRow,
                'row_type' => 'agent',
            ];
        }
        $gtSa += $subSa;
        $gtOn += $subOn;
        $gtResch += $subResch;
        $gtWait += $subWait;
        $gtRef += $subRef;
        $gtOther += $subOther;
        $gtTot += $subTot;
        foreach ($todayCols as $colNm) {
            $gtStatuses[$colNm] += $subStatuses[$colNm];
        }
        $todayRows[] = [
            'leader' => $ldr,
            'salesname' => $ldr . ' Total',
            'sa' => $subSa,
            'on_installation' => $subOn,
            'reschedule' => $subResch,
            'refund' => $subRef,
            'waiting_wo' => $subWait,
            'other' => $subOther,
            'total' => $subTot,
            'statuses' => $subStatuses,
            'row_type' => 'leader_total',
        ];
    }
    if ($todayRows) {
        $todayRows[] = [
            'leader' => 'Grand Total',
            'salesname' => 'Grand Total',
            'sa' => $gtSa,
            'on_installation' => $gtOn,
            'reschedule' => $gtResch,
            'refund' => $gtRef,
            'waiting_wo' => $gtWait,
            'other' => $gtOther,
            'total' => $gtTot,
            'statuses' => $gtStatuses,
            'row_type' => 'grand_total',
        ];
    }

    $waitingPivot = susun_pivot_wo_1kolom($waitingByLdrAgent);
    $besokPivot = susun_pivot_wo_1kolom($besokByLdrAgent);

    $sumLeaders = array_keys($summaryLdr);
    usort($sumLeaders, 'strnatcasecmp');
    $leaderSummaryRows = [];
    foreach ($sumLeaders as $ldr) {
        $rowS = $summaryLdr[$ldr];
        $rowS['is_grand_total'] = false;
        $leaderSummaryRows[] = $rowS;
    }
    if ($leaderSummaryRows) {
        $leaderSummaryRows[] = [
            'leader' => 'Grand Total',
            'today_sa' => $gtSa,
            'today_on_installation' => $gtOn,
            'today_reschedule' => $gtResch,
            'today_waiting_wo' => $gtWait,
            'today_refund' => $gtRef,
            'today_other' => $gtOther,
            'today_total' => $gtTot,
            'wo_besok' => $besokPivot['grand_total'],
            'waiting_wo' => $waitingPivot['grand_total'],
            'is_grand_total' => true,
        ];
    }

    $agentSummaryRows = [];
    foreach ($sumLeaders as $ldr) {
        $agMapS = $summaryAgent[$ldr] ?? [];
        $agNamesS = array_keys($agMapS);
        usort($agNamesS, 'strnatcasecmp');
        foreach ($agNamesS as $snS) {
            $agentSummaryRows[] = $agMapS[$snS];
        }
    }

    return [
        'calc_version' => 2,
        'day' => $hariValid,
        'today_label' => $todayLabel,
        'besok_label' => $besokLabel,
        'besok_range_label' => '>= ' . $besokLabel,
        'available_days' => daftar_hari_wo_tersedia($prospect, $bulan, $tahun, $hariValid),
        'wo_today_columns' => $todayCols,
        'wo_today_rows' => $todayRows,
        'wo_today_totals' => [
            'sa' => $gtSa,
            'on_installation' => $gtOn,
            'reschedule' => $gtResch,
            'refund' => $gtRef,
            'waiting_wo' => $gtWait,
            'other' => $gtOther,
            'total' => $gtTot,
            'statuses' => $todayStatusTotals,
        ],
        'wo_today_other_statuses' => [],
        'wo_besok_rows' => $besokPivot['rows'],
        'wo_besok_total' => $besokPivot['grand_total'],
        'wo_besok_h1_total' => $besokH1Total,
        'wo_besok_later_total' => $besokLaterTotal,
        'waiting_wo_rows' => $waitingPivot['rows'],
        'waiting_wo_total' => $waitingPivot['grand_total'],
        'waiting_wo_breakdown' => $waitingBreakdown,
        'leader_summary' => $leaderSummaryRows,
        'agent_summary' => $agentSummaryRows,
    ];
}

/* ------------------------------------------------------------------------- */
/* PROSES UTAMA                                                                */
/* ------------------------------------------------------------------------- */

/**
 * @param array{target_path:string,prospects:list<array{path:string,name:string}>,sheet:string,bulan_lalu:int,bulan_ini:int,tahun:int,total_hari:int,hari_berjalan:int,rasio_paid:float,hari_harian?:int,hari_wo?:int} $o
 * @return array<string,mixed> payload (struktur sama dengan data_komisi.json)
 */
function proses_data(array $o): array
{
    @ini_set('memory_limit', '768M');
    @set_time_limit(300);

    $bulanLalu = (int)$o['bulan_lalu'];
    $bulanIni = (int)$o['bulan_ini'];
    $tahun = (int)$o['tahun'];
    $totalHari = (int)$o['total_hari'];
    $hari = (int)$o['hari_berjalan'];
    $hariHarian = isset($o['hari_harian']) ? (int)$o['hari_harian'] : $hari;
    $hariWo = isset($o['hari_wo']) ? (int)$o['hari_wo'] : $hariHarian;
    $rasio = (float)$o['rasio_paid'];

    $sisaHari = max(1, $totalHari - $hari);
    $sisaMinggu = max(1, (int)ceil($sisaHari / 7.0));
    $targetMtd = round_excel(($hari / (float)max(1, $totalHari)) * 100.0);

    $hariDlmBulan = (int)cal_days_in_month_aman($bulanIni, $tahun);
    $tglAcuan = new DateTimeImmutable(sprintf('%04d-%02d-%02d', $tahun, $bulanIni, min($hari, $hariDlmBulan)));

    // 1. Target
    $target = baca_data_target($o['target_path'], $o['sheet'], $tglAcuan);
    if (!$target) {
        throw new RuntimeException('Tidak ada data agen yang terbaca dari sheet "' . $o['sheet'] . '" pada file Target. Pastikan sheet berisi blok "TEAM ... NAMA" dan nama sheet sudah benar.');
    }

    // 2. Prospect (bersihkan duplikat pool awal + perbarui bulan penuh/baris terbaru tanpa duplikat)
    $poolByKey = [];
    $infoFile = [];
    $adaPayment = true;
    if (!empty($o['prospect_rows_awal']) && is_array($o['prospect_rows_awal'])) {
        $poolByKey = deduplikasi_pool_rows($o['prospect_rows_awal']);
        $masukAwal = count($poolByKey);
        if ($masukAwal > 0) {
            $infoFile[] = ['name' => 'Database Server Aktif', 'rows' => count($o['prospect_rows_awal']), 'rows_baru' => $masukAwal];
        }
    }
    foreach (($o['prospects'] ?? []) as $pf) {
        $b = baca_file_prospect($pf['path'], $pf['name']);
        $adaPayment = $adaPayment && $b['ada_payment'];
        // Jika file baru memuat 1 bulan penuh (>= 50 baris Created pada bulan tsb), ganti bersih data bulan tsb agar baris batal/edit tidak tertinggal
        $bulanPenuh = deteksi_bulan_penuh_rows($b['rows']);
        if (!empty($bulanPenuh) && !empty($poolByKey)) {
            foreach ($poolByKey as $pkExisting => $rowExisting) {
                $crEx = isset($rowExisting[P_CREATED]) && $rowExisting[P_CREATED] !== null ? (int)$rowExisting[P_CREATED] : 0;
                $ymEx = $crEx >= 20000101 ? intdiv($crEx, 100) : 0;
                if ($ymEx > 0 && isset($bulanPenuh[$ymEx])) {
                    unset($poolByKey[$pkExisting]);
                }
            }
        }
        $masuk = 0;
        foreach ($b['rows'] as $row) {
            $k = (string)$row[8];
            if (!isset($poolByKey[$k])) {
                $masuk++;
            }
            $poolByKey[$k] = $row;
        }
        $infoFile[] = ['name' => $pf['name'], 'rows' => count($b['rows']), 'rows_baru' => $masuk];
    }
    $prospect = array_values($poolByKey);
    unset($poolByKey);
    if (!$prospect) {
        throw new RuntimeException('Tidak ada baris data pada file prospect.');
    }
    if (!empty($o['simpan_pool_path'])) {
        @file_put_contents($o['simpan_pool_path'], gzencode(json_encode($prospect, JSON_UNESCAPED_UNICODE), 6));
    }

    // 3. Filter MTD
    $mtdLalu = filter_mtd($prospect, P_ACTIVE, $bulanLalu, $tahun, $hari, true, null);
    $mtdIni = filter_mtd($prospect, P_ACTIVE, $bulanIni, $tahun, $hari, true, null);
    $mtdPaid = filter_mtd($prospect, P_PAYMENT, $bulanIni, $tahun, $hari, false, true);
    $mtdSo = filter_mtd($prospect, P_CREATED, $bulanIni, $tahun, $hari, false, null);

    $kolOct = 'SA ' . (NAMA_BULAN_SINGKAT[$bulanLalu] ?? 'OCT') . ' 1-' . $hari;
    $kolNov = 'SA ' . (NAMA_BULAN_SINGKAT[$bulanIni] ?? 'NOV') . ' 1-' . $hari;

    // 4. Tabel MTD SA per Sales Leader
    $setLeader = [];
    foreach ($prospect as $r) {
        $l = trim((string)$r[P_LDR]);
        if ($l !== '') {
            $setLeader[$l] = true;
        }
    }
    foreach ($target as $t) {
        $l = (string)$t['Leader_Default'];
        if ($l !== '') {
            $setLeader[$l] = true;
        }
    }
    $semuaLeader = array_keys($setLeader);
    sort($semuaLeader, SORT_STRING);

    $hitungPerLeader = function (array $rows): array {
        $c = [];
        foreach ($rows as $r) {
            $l = (string)$r[P_LDR];
            $c[$l] = ($c[$l] ?? 0) + 1;
        }
        return $c;
    };
    $cLalu = $hitungPerLeader($mtdLalu);
    $cIni = $hitungPerLeader($mtdIni);

    $mtdRows = [];
    foreach ($semuaLeader as $l) {
        $a = (int)($cLalu[$l] ?? 0);
        $b = (int)($cIni[$l] ?? 0);
        if ($a > 0 || $b > 0) {
            $mtdRows[] = ['leader' => $l, 'sa_oct' => $a, 'sa_nov' => $b, 'gap_sa' => $b - $a];
        }
    }
    usort($mtdRows, function ($x, $y) {
        return [$y['gap_sa'], $y['sa_nov']] <=> [$x['gap_sa'], $x['sa_nov']];
    });
    $totOct = array_sum(array_column($mtdRows, 'sa_oct'));
    $totNov = array_sum(array_column($mtdRows, 'sa_nov'));
    $mtdRows[] = ['leader' => 'Total', 'sa_oct' => (int)$totOct, 'sa_nov' => (int)$totNov, 'gap_sa' => (int)($totNov - $totOct)];

    // 5. Agregasi per agen
    $peta = [];
    foreach ($prospect as $r) {
        $kunci = normalisasi_nama_agen($r[P_SLS]);
        if (in_array($kunci, ['', 'NAN', 'NONE', 'TOTAL', '-'], true)) {
            continue;
        }
        if ($r[P_SLS] !== null && $r[P_SLS] !== '') {
            $peta[$kunci] = $r[P_SLS];
        }
    }
    $agg = function (array $rows): array {
        $c = [];
        foreach ($rows as $r) {
            $k = normalisasi_nama_agen($r[P_SLS]);
            $c[$k] = ($c[$k] ?? 0) + 1;
        }
        return $c;
    };
    $soPerAgen = $agg($mtdSo);
    $paidPerAgen = $agg($mtdPaid);
    $saPerAgen = [];
    foreach ($mtdIni as $r) {
        $k = normalisasi_nama_agen($r[P_SLS]);
        if (!isset($saPerAgen[$k])) {
            $saPerAgen[$k] = ['sa' => 0, '3m' => 0, 'm' => 0, 'sem' => 0, 'yr' => 0, 'rev' => 0.0];
        }
        $tp = u_upper(trim((string)$r[P_TIPE]));
        $saPerAgen[$k]['sa']++;
        $saPerAgen[$k]['rev'] += (float)$r[P_HARGA];
        if ($tp === '3 MONTHLY' || $tp === '3MONTHLY') {
            $saPerAgen[$k]['3m']++;
        } elseif ($tp === 'MONTHLY') {
            $saPerAgen[$k]['m']++;
        } elseif ($tp === 'SEMESTERLY') {
            $saPerAgen[$k]['sem']++;
        } elseif ($tp === 'YEARLY') {
            $saPerAgen[$k]['yr']++;
        }
    }

    // 6. Detail agen
    $agen = [];
    foreach ($target as $t) {
        $key = $t['Agent_Key'];
        $sa = (int)($saPerAgen[$key]['sa'] ?? 0);
        $paid = (int)($paidPerAgen[$key] ?? 0);
        $so = (int)($soPerAgen[$key] ?? 0);
        $rev = (float)($saPerAgen[$key]['rev'] ?? 0.0);
        $tAll = (int)$t['TARGET ALL'];

        $gap = $sa - $tAll;
        $pct = $tAll > 0 ? round_excel(($sa / (float)$tAll) * 100.0) : 0;
        $runrate = round_excel(((float)$sa * (float)$totalHari) / (float)max(1, $hari));
        $targetSaMtd = (int)ceil($tAll * ((float)$hari / (float)max(1, $totalHari)));
        $kurangMtd = max(0, $targetSaMtd - $sa);
        $sisaSa = max(0, $tAll - $sa);
        $harusSaDes = $sisaSa / (float)$sisaHari;
        $harusSa = (int)ceil($harusSaDes);
        $harusPaid = max($harusSa, (int)ceil($harusSaDes * $rasio));
        $harusSo = (int)ceil($harusPaid * 1.25);
        $saMgg = (int)ceil($sisaSa / (float)$sisaMinggu);
        $paidMgg = (int)ceil($saMgg * $rasio);
        $revNetto = $rev * 0.89;
        $komisi = ($tAll > 0 && $sa >= $tAll) ? $revNetto * 0.35 : $revNetto * 0.20;

        $nama = isset($peta[$key]) ? trim((string)$peta[$key]) : trim((string)$t['Nama_Tampil']);

        $agen[] = [
            'leader' => trim((string)$t['Leader_Default']),
            'name' => $nama,
            'agent_key' => $key,
            'masa_kerja' => $t['Masa Kerja'] !== '' ? $t['Masa Kerja'] : '-',
            'level' => $t['Level'] !== '' ? $t['Level'] : '-',
            'target_all' => $tAll,
            'target_reguler' => (int)$t['Target Reguler'],
            'target_yearly' => (int)$t['Target Yearly'],
            'sa_nov' => $sa,
            'paid_nov' => $paid,
            'so_nov' => $so,
            'gap_sa' => $gap,
            'persen' => $pct,
            'status_mtd' => $pct < $targetMtd
                ? '⚠️ MASIH KURANG (-' . ($targetMtd - $pct) . '%)'
                : '✅ ON-TRACK (>= ' . $targetMtd . '%)',
            'kurang_sa_mtd' => $kurangMtd,
            'harus_paid_hr' => $harusPaid,
            'harus_sa_hr' => $harusSa,
            'harus_sa_des' => round($harusSaDes, 2),
            'harus_so_hr' => $harusSo,
            'harus_paid_mgg' => $paidMgg,
            'harus_sa_mgg' => $saMgg,
            'daily_norm' => (int)$t['Daily Paid Normal'],
            'runrate_30' => $runrate,
            'p_3m' => (int)($saPerAgen[$key]['3m'] ?? 0),
            'p_m' => (int)($saPerAgen[$key]['m'] ?? 0),
            'p_sem' => (int)($saPerAgen[$key]['sem'] ?? 0),
            'p_yr' => (int)($saPerAgen[$key]['yr'] ?? 0),
            'rev_kotor' => round($rev, 0),
            'rev_netto' => round($revNetto, 0),
            'tier_komisi' => ($tAll > 0 && $sa >= $tAll) ? '35% (Capai Target)' : '20% (Belum Capai)',
            'est_komisi' => round($komisi, 0),
        ];
    }

    // Urutan: persentase tim tertinggi, leader A-Z, vacant di bawah, persen & SA tertinggi
    $sumSa = [];
    $sumTarget = [];
    foreach ($agen as $a) {
        $sumSa[$a['leader']] = ($sumSa[$a['leader']] ?? 0) + $a['sa_nov'];
        $sumTarget[$a['leader']] = ($sumTarget[$a['leader']] ?? 0) + $a['target_all'];
    }
    $pctLeader = [];
    foreach ($sumSa as $l => $s) {
        $pctLeader[$l] = (float)$s / (float)max(1, $sumTarget[$l]);
    }
    usort($agen, function ($x, $y) use ($pctLeader) {
        $vx = strtoupper($x['name']) === 'VACANT' ? 1 : 0;
        $vy = strtoupper($y['name']) === 'VACANT' ? 1 : 0;
        return [$pctLeader[$y['leader']], $x['leader'], $vx, $y['persen'], $y['sa_nov']]
            <=> [$pctLeader[$x['leader']], $y['leader'], $vy, $x['persen'], $x['sa_nov']];
    });

    // 7. Rekap Harian (SO, PAID, SA) & Jumlah Agent Belum Produktif per Sales Leader
    $dailyProd = hitung_rekap_harian_blm_produktif($prospect, $target, $bulanIni, $tahun, $hariHarian);
    $tglTersedia = daftar_hari_tersedia_bulan($prospect, $bulanIni, $tahun, $hariHarian);

    // 8. Monitoring Work Order (WO TODAY | WAITING WO | WO BESOK)
    $woSummary = hitung_wo_laporan($prospect, $bulanIni, $tahun, $hariWo);

    $namaBln = NAMA_BULAN_TAMPIL[$bulanIni] ?? 'Nov';
    return [
        'calc_engine_version' => 3,
        'periode_label' => $hari . '-' . $namaBln . '-' . $tahun,
        'hari_berjalan' => $hari,
        'total_hari' => $totalHari,
        'sisa_hari' => $sisaHari,
        'sisa_minggu' => $sisaMinggu,
        'target_persen_mtd' => $targetMtd,
        'kol_oct' => $kolOct,
        'kol_nov' => $kolNov,
        'label_bulan_lalu' => NAMA_BULAN_SINGKAT[$bulanLalu] ?? 'OCT',
        'label_bulan_ini' => NAMA_BULAN_SINGKAT[$bulanIni] ?? 'NOV',
        'daily_prod_date_label' => $dailyProd['date_label'],
        'daily_prod_day' => $dailyProd['day'],
        'daily_prod_rows' => $dailyProd['rows'],
        'tanggal_tersedia' => $tglTersedia,
        'wo_summary' => $woSummary,
        'params' => [
            'sheet' => $o['sheet'],
            'bulan_lalu' => $bulanLalu,
            'bulan_ini' => $bulanIni,
            'tahun' => $tahun,
            'total_hari' => $totalHari,
            'hari_berjalan' => $hari,
            'hari_harian' => $dailyProd['day'],
            'hari_wo' => $woSummary['day'],
            'rasio_paid' => $rasio,
        ],
        'sumber' => ['target' => basename($o['target_name'] ?? $o['target_path']), 'prospect' => $infoFile, 'total_baris_prospect' => count($prospect)],
        'mtd_rows' => $mtdRows,
        'agent_rows' => $agen,
    ];
}

function cal_days_in_month_aman(int $bulan, int $tahun): int
{
    if (function_exists('cal_days_in_month')) {
        return cal_days_in_month(CAL_GREGORIAN, $bulan, $tahun);
    }
    return (int)(new DateTimeImmutable(sprintf('%04d-%02d-01', $tahun, $bulan)))->format('t');
}

