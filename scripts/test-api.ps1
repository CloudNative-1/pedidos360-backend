[CmdletBinding()]
param(
    [ValidateSet('NoToken', 'Authorization', 'Preflight', 'CatalogCrud', 'OrderFlow', 'All')]
    [string]$Scenario = 'NoToken',
    [string]$BaseUrl = 'https://o3k66b0owk.execute-api.us-east-1.amazonaws.com',
    [string]$AdminToken = $env:PEDIDOS360_TOKEN_ADMIN,
    [string]$ClienteToken = $env:PEDIDOS360_TOKEN_CLIENTE
)

$ErrorActionPreference = 'Stop'
$BaseUrl = $BaseUrl.TrimEnd('/')

function Invoke-PedidosRequest {
    param(
        [Parameter(Mandatory)][string]$Method,
        [Parameter(Mandatory)][string]$Path,
        [string]$Token,
        [object]$Body,
        [hashtable]$ExtraHeaders = @{}
    )

    $headers = @{ Accept = 'application/json' }
    if ($Token) { $headers.Authorization = "Bearer $Token" }
    foreach ($key in $ExtraHeaders.Keys) { $headers[$key] = $ExtraHeaders[$key] }

    $request = @{
        Uri = "$BaseUrl$Path"
        Method = $Method
        Headers = $headers
        UseBasicParsing = $true
        ErrorAction = 'Stop'
    }
    if ($null -ne $Body) {
        $request.ContentType = 'application/json'
        $request.Body = ConvertTo-Json -InputObject $Body -Depth 10 -Compress
    }

    try {
        $response = Invoke-WebRequest @request
        return [pscustomobject]@{
            Status = [int]$response.StatusCode
            Body = [string]$response.Content
            Headers = $response.Headers
        }
    }
    catch {
        $response = $_.Exception.Response
        if ($null -eq $response) { throw }
        $reader = New-Object System.IO.StreamReader($response.GetResponseStream())
        try { $content = $reader.ReadToEnd() } finally { $reader.Dispose() }
        return [pscustomobject]@{
            Status = [int]$response.StatusCode
            Body = $content
            Headers = $response.Headers
        }
    }
}

function Assert-Status {
    param([int]$Actual, [int]$Expected, [string]$Action)
    if ($Actual -ne $Expected) { throw "$Action devolvió HTTP $Actual; se esperaba $Expected." }
    Write-Host "$Action -> HTTP $Actual"
}

function Convert-BodyToObject {
    param([string]$Body)
    if (-not $Body) { return $null }
    return ConvertFrom-Json -InputObject $Body
}

function Require-Token {
    param([string]$Value, [string]$Name)
    if (-not $Value) { throw "Falta $Name. Define la variable local y vuelve a ejecutar." }
    return $Value
}

function Test-NoToken {
    $result = Invoke-PedidosRequest -Method GET -Path '/catalogo'
    Assert-Status $result.Status 401 'GET /catalogo sin token'
}

function Test-Authorization {
    $admin = Require-Token $AdminToken 'PEDIDOS360_TOKEN_ADMIN'
    $cliente = Require-Token $ClienteToken 'PEDIDOS360_TOKEN_CLIENTE'
    $result = Invoke-PedidosRequest -Method GET -Path '/catalogo' -Token $admin
    Assert-Status $result.Status 200 'GET /catalogo como Admin'
    $result = Invoke-PedidosRequest -Method GET -Path '/catalogo' -Token $cliente
    Assert-Status $result.Status 403 'GET /catalogo como Cliente (requiere catalog.read en el token)'
}

function Test-Preflight {
    $headers = @{
        Origin = 'http://localhost:5173'
        'Access-Control-Request-Method' = 'GET'
        'Access-Control-Request-Headers' = 'authorization,content-type'
    }
    $result = Invoke-PedidosRequest -Method OPTIONS -Path '/catalogo' -ExtraHeaders $headers
    $origin = $result.Headers['Access-Control-Allow-Origin']
    $methods = $result.Headers['Access-Control-Allow-Methods']
    $allowedHeaders = $result.Headers['Access-Control-Allow-Headers']
    if ($origin -ne 'http://localhost:5173') { throw 'El preflight no devolvió el origen permitido esperado.' }
    if (-not $methods -or $methods -notmatch 'GET') { throw 'El preflight no anunció GET en Access-Control-Allow-Methods.' }
    foreach ($header in @('authorization', 'content-type', 'accept')) {
        if (-not $allowedHeaders -or $allowedHeaders -notmatch $header) { throw "El preflight no permitió el header $header." }
    }
    Write-Host "OPTIONS /catalogo -> HTTP $($result.Status); CORS origin, método y headers comprobados"
}

function Test-CatalogCrud {
    $admin = Require-Token $AdminToken 'PEDIDOS360_TOKEN_ADMIN'
    $id = $null
    try {
        $createdResponse = Invoke-PedidosRequest -Method POST -Path '/catalogo' -Token $admin -Body @{
            nombre = 'Producto de prueba Pedidos360'
            descripcion = 'Temporal para smoke test'
            precio = 100
            stock = 2
        }
        Assert-Status $createdResponse.Status 201 'POST /catalogo'
        $product = Convert-BodyToObject $createdResponse.Body
        $id = [string]$product.id
        if (-not $id) { throw 'POST /catalogo no devolvió id.' }

        $result = Invoke-PedidosRequest -Method GET -Path "/catalogo/$([uri]::EscapeDataString($id))" -Token $admin
        Assert-Status $result.Status 200 'GET /catalogo/{id}'
        $result = Invoke-PedidosRequest -Method PUT -Path "/catalogo/$([uri]::EscapeDataString($id))" -Token $admin -Body @{ stock = 3 }
        Assert-Status $result.Status 200 'PUT /catalogo/{id}'
        $result = Invoke-PedidosRequest -Method DELETE -Path "/catalogo/$([uri]::EscapeDataString($id))" -Token $admin
        Assert-Status $result.Status 204 'DELETE /catalogo/{id}'
        $id = $null
    }
    finally {
        if ($id) {
            try { [void](Invoke-PedidosRequest -Method DELETE -Path "/catalogo/$id" -Token $admin) }
            catch { Write-Warning "Limpieza pendiente: borrar el producto temporal $id manualmente." }
        }
    }
}

function Test-OrderFlow {
    $admin = Require-Token $AdminToken 'PEDIDOS360_TOKEN_ADMIN'
    $cliente = Require-Token $ClienteToken 'PEDIDOS360_TOKEN_CLIENTE'
    $productId = $null
    $orderId = $null
    try {
        $createdProduct = Invoke-PedidosRequest -Method POST -Path '/catalogo' -Token $admin -Body @{
            nombre = 'Producto temporal de stock'
            descripcion = 'Creado por test-api.ps1'
            precio = 100
            stock = 2
        }
        Assert-Status $createdProduct.Status 201 'POST /catalogo (stock demo)'
        $product = Convert-BodyToObject $createdProduct.Body
        $productId = [string]$product.id

        $orderResponse = Invoke-PedidosRequest -Method POST -Path '/pedidos' -Token $cliente -Body @{
            productos = @(@{ productoId = $productId; cantidad = 1 })
        }
        Assert-Status $orderResponse.Status 201 'POST /pedidos como Cliente'
        $order = Convert-BodyToObject $orderResponse.Body
        $orderId = [string]$order.id
        if ($order.estado -ne 'CREADO') { throw 'El pedido nuevo no inició en CREADO.' }

        $productResponse = Invoke-PedidosRequest -Method GET -Path "/catalogo/$productId" -Token $admin
        $stockAtCreation = (Convert-BodyToObject $productResponse.Body).stock
        if ($stockAtCreation -ne 2) { throw 'Crear el pedido modificó stock antes de aceptar.' }

        $result = Invoke-PedidosRequest -Method GET -Path '/pedidos' -Token $cliente
        Assert-Status $result.Status 200 'GET /pedidos como Cliente'
        $result = Invoke-PedidosRequest -Method GET -Path "/pedidos/$orderId" -Token $cliente
        Assert-Status $result.Status 200 'GET /pedidos/{id} como Cliente'

        $result = Invoke-PedidosRequest -Method PUT -Path "/pedidos/$orderId/estado" -Token $admin -Body @{ estado = 'ACEPTADO' }
        Assert-Status $result.Status 200 'CREADO -> ACEPTADO'
        $productResponse = Invoke-PedidosRequest -Method GET -Path "/catalogo/$productId" -Token $admin
        if ((Convert-BodyToObject $productResponse.Body).stock -ne 1) { throw 'Aceptar el pedido no descontó una unidad.' }

        $result = Invoke-PedidosRequest -Method PUT -Path "/pedidos/$orderId/estado" -Token $admin -Body @{ estado = 'EN_PREPARACION' }
        Assert-Status $result.Status 200 'ACEPTADO -> EN_PREPARACION'
        $result = Invoke-PedidosRequest -Method PUT -Path "/pedidos/$orderId/estado" -Token $admin -Body @{ estado = 'CANCELADO' }
        Assert-Status $result.Status 200 'EN_PREPARACION -> CANCELADO'
        $productResponse = Invoke-PedidosRequest -Method GET -Path "/catalogo/$productId" -Token $admin
        if ((Convert-BodyToObject $productResponse.Body).stock -ne 2) { throw 'Cancelar no restauró el stock.' }
    }
    finally {
        if ($orderId) {
            try {
                $current = Invoke-PedidosRequest -Method GET -Path "/pedidos/$orderId" -Token $admin
                if ($current.Status -eq 200) {
                    $currentOrder = Convert-BodyToObject $current.Body
                    if ($currentOrder.estado -in @('CREADO', 'ACEPTADO', 'EN_PREPARACION')) {
                        [void](Invoke-PedidosRequest -Method PUT -Path "/pedidos/$orderId/estado" -Token $admin -Body @{ estado = 'CANCELADO' })
                    }
                }
            }
            catch { Write-Warning "Limpieza pendiente: revisar pedido temporal $orderId y cancelar si corresponde." }
        }
        if ($productId) {
            try { [void](Invoke-PedidosRequest -Method DELETE -Path "/catalogo/$productId" -Token $admin) }
            catch { Write-Warning "Limpieza pendiente: revisar producto temporal $productId." }
        }
    }
}

switch ($Scenario) {
    'NoToken' { Test-NoToken }
    'Authorization' { Test-Authorization }
    'Preflight' { Test-Preflight }
    'CatalogCrud' { Test-CatalogCrud }
    'OrderFlow' { Test-OrderFlow }
    'All' {
        Test-NoToken
        Test-Preflight
        Test-Authorization
        Test-CatalogCrud
        Test-OrderFlow
    }
}
