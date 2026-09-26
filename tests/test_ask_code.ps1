$ErrorActionPreference = 'Stop'
$launcher = Join-Path (Split-Path $PSScriptRoot -Parent) 'ask-code.ps1'
$fixture = Join-Path ([IO.Path]::GetTempPath()) ('ollama-launcher-test-' + [guid]::NewGuid())
[IO.Directory]::CreateDirectory($fixture) | Out-Null
$source = Join-Path $fixture 'sample.py'

function Read-Host {
    param($Prompt)
    if ($global:ollamaTestAnswers.Count -eq 0) { throw "Unexpected prompt: $Prompt" }
    return $global:ollamaTestAnswers.Dequeue()
}
function Invoke-RestMethod {
    param($Uri, $Method, $ContentType, $Body, $TimeoutSec)
    $request = [Text.Encoding]::UTF8.GetString($Body) | ConvertFrom-Json
    $global:ollamaTestRequests += ,$request
    if ([IO.File]::ReadAllText($source) -cne 'value = 1') { throw 'Unapproved edits were written.' }
    if ($request.messages[-1].content -notmatch 'value = 1') { throw 'Source was not included.' }
    if ($global:ollamaTestScenario -eq 'conflict') { [IO.File]::WriteAllText($source, 'value = 3') }
    $editPath = if ($global:ollamaTestScenario -eq 'escape') { '..\outside.py' } else { 'sample.py' }
    return @{ message = @{content = (@{answer='Test proposal'; edits=@(@{path=$editPath; old='value = 1'; new='value = 2'})} | ConvertTo-Json -Depth 5)} }
}

foreach ($case in @('approve', 'skip', 'conflict', 'escape', 'redo', 'retry')) {
    $global:ollamaTestScenario = $case
    [IO.File]::WriteAllText($source, 'value = 1')
    $global:ollamaTestAnswers = [Collections.Generic.Queue[string]]::new()
    $global:ollamaTestRequests = @()
    $global:ollamaTestAnswers.Enqueue('Change value to 2')
    if ($case -in @('redo', 'retry')) {
        $global:ollamaTestAnswers.Enqueue('REDO')
        $global:ollamaTestAnswers.Enqueue($(if ($case -eq 'redo') { 'Set value to 2 and explain why' } else { '' }))
        $global:ollamaTestAnswers.Enqueue('SKIP')
    } elseif ($case -ne 'escape') { $global:ollamaTestAnswers.Enqueue($(if ($case -eq 'skip') { '' } else { 'APPLY' })) }
    $global:ollamaTestAnswers.Enqueue('/quit')
    & $launcher -Root $fixture
    $expected = switch ($case) { approve {'value = 2'} conflict {'value = 3'} default {'value = 1'} }
    if ([IO.File]::ReadAllText($source) -cne $expected) { throw "Failed case: $case" }
    if ($global:ollamaTestAnswers.Count) { throw "Unconsumed input in case: $case" }
    if ($case -in @('redo', 'retry')) {
        if ($global:ollamaTestRequests.Count -ne 2) { throw 'REDO did not resend.' }
        $second = $global:ollamaTestRequests[1]
        $expectedPrompt = if ($case -eq 'redo') { 'Set value to 2 and explain why' } else { 'Change value to 2' }
        if ($second.messages.Count -ne 2 -or -not $second.messages[-1].content.Contains($expectedPrompt)) { throw 'Retry prompt/history was incorrect.' }
    }
    Write-Host "PASS: $case"
}
$backups = @(Get-ChildItem -LiteralPath (Join-Path $fixture '.ollama-backups') -Recurse -File)
if ($backups.Count -ne 1 -or [IO.File]::ReadAllText($backups[0].FullName) -cne 'value = 1') { throw 'Backup failed.' }
Write-Host "PASS: original bytes backed up. Fixtures retained at $fixture"

. (Join-Path (Split-Path $PSScriptRoot -Parent) 'ask-code-menu.ps1')
foreach ($navigation in @(
    @{Keys=@('Enter'); Expected='APPLY'},
    @{Keys=@('DownArrow', 'Enter'); Expected='REDO'},
    @{Keys=@('UpArrow', 'Enter'); Expected='REDO'},
    @{Keys=@('DownArrow', 'UpArrow', 'Enter'); Expected='APPLY'},
    @{Keys=@('Escape'); Expected='SKIP'}
)) {
    $global:ollamaMenuKeys = [Collections.Generic.Queue[string]]::new()
    foreach ($key in $navigation.Keys) { $global:ollamaMenuKeys.Enqueue($key) }
    $result = Select-EditAction -ReadKey { $global:ollamaMenuKeys.Dequeue() }
    if ($result -ne $navigation.Expected) { throw 'Menu navigation failed.' }
}
Write-Host 'PASS: arrow navigation, Enter, and Escape'

$folderWithSpaces = Join-Path $fixture 'another project [test]'
[IO.Directory]::CreateDirectory($folderWithSpaces) | Out-Null
foreach ($folderCase in @(
    @{Answers=@('"' + $folderWithSpaces + '"'); Expected=$folderWithSpaces},
    @{Answers=@("'" + $folderWithSpaces + "'"); Expected=$folderWithSpaces},
    @{Answers=@(''); Expected=$fixture},
    @{Answers=@((Join-Path $fixture 'missing'), $source, $folderWithSpaces); Expected=$folderWithSpaces}
)) {
    $global:ollamaTestAnswers = [Collections.Generic.Queue[string]]::new()
    foreach ($answer in $folderCase.Answers) { $global:ollamaTestAnswers.Enqueue($answer) }
    $result = Read-ProjectFolder -DefaultPath $fixture
    if ($result -ne $folderCase.Expected -or $global:ollamaTestAnswers.Count) { throw 'Folder selection failed.' }
}
Write-Host 'PASS: pasted quoted paths, spaces, literal brackets, default folder, and invalid-path retry'
