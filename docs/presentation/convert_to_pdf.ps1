$ErrorActionPreference = "Stop"

$src = "C:\Users\jaewo\Desktop\SkyOps Intelligence\docs\presentation\SkyOps_Intelligence_최종보고서.docx"
$dst = "C:\Users\jaewo\Desktop\SkyOps Intelligence\docs\presentation\SkyOps_Intelligence_최종보고서.pdf"

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    Write-Host "MS_WORD_VERSION: $($word.Version)"

    $doc = $word.Documents.Open($src, $false, $true)
    # wdFormatPDF = 17
    $doc.SaveAs([ref] $dst, [ref] 17)
    $doc.Close($false)
    $word.Quit()

    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($doc) | Out-Null
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
    [GC]::Collect()
    [GC]::WaitForPendingFinalizers()

    Write-Host "PDF_SAVED: $dst"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)"
    exit 2
}
