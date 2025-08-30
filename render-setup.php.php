<?php
// Render.com specific setup
$port = getenv('PORT') ?: '80';
$host = getenv('RENDER_EXTERNAL_HOSTNAME') ?: 'localhost';

// Update webhook URL automatically
if (getenv('RENDER')) {
    $webhookUrl = "https://$host";
    putenv("WEBHOOK_URL=$webhookUrl");
    
    error_log("Render.com environment detected");
    error_log("Webhook URL set to: $webhookUrl");
    error_log("Server running on port: $port");
}

// Health check endpoint for Render
if (isset($_GET['health'])) {
    header('Content-Type: application/json');
    echo json_encode([
        'status' => 'ok',
        'timestamp' => date('c'),
        'environment' => getenv('RENDER') ? 'production' : 'development',
        'port' => $port,
        'host' => $host
    ]);
    exit;
}
?>