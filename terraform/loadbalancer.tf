# ── Global HTTPS Load Balancer + Cloud DNS for sismicamarina.cl ───────────────
#
# Architecture:
#   Internet → static IP → forwarding rule → HTTPS proxy → URL map
#                                                          → backend service
#                                                          → Serverless NEG
#                                                          → Cloud Run (frontend)
#
#   HTTP (port 80) is permanently redirected to HTTPS.
#
# After `terraform apply`, copy the `dns_nameservers` output and update your
# domain registrar (NIC Chile / nic.cl) to delegate sismicamarina.cl to those
# nameservers. The managed SSL certificate activates automatically once DNS
# propagates (can take up to 30 minutes).

# ── Static IP ─────────────────────────────────────────────────────────────────

resource "google_compute_global_address" "frontend_lb_ip" {
  name = "${var.project_name}-frontend-lb-ip"
}

# ── Serverless NEG (Cloud Run → Load Balancer bridge) ─────────────────────────

resource "google_compute_region_network_endpoint_group" "frontend_neg" {
  name                  = "${var.project_name}-frontend-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_v2_service.frontend.name
  }
}

# ── Backend service ────────────────────────────────────────────────────────────

resource "google_compute_backend_service" "frontend_backend" {
  name                  = "${var.project_name}-frontend-backend"
  load_balancing_scheme = "EXTERNAL_MANAGED"
  protocol              = "HTTPS"

  backend {
    group = google_compute_region_network_endpoint_group.frontend_neg.id
  }
}

# ── URL maps ──────────────────────────────────────────────────────────────────

resource "google_compute_url_map" "frontend_lb" {
  name            = "${var.project_name}-frontend-lb"
  default_service = google_compute_backend_service.frontend_backend.id
}

# Separate URL map that permanently redirects HTTP → HTTPS.
resource "google_compute_url_map" "https_redirect" {
  name = "${var.project_name}-https-redirect"

  default_url_redirect {
    https_redirect         = true
    redirect_response_code = "MOVED_PERMANENTLY_DEFAULT"
    strip_query            = false
  }
}

# ── Managed SSL certificate ────────────────────────────────────────────────────

resource "google_compute_managed_ssl_certificate" "frontend_ssl" {
  name = "${var.project_name}-frontend-ssl"

  managed {
    domains = [var.domain, "www.${var.domain}"]
  }
}

# ── HTTPS proxy ────────────────────────────────────────────────────────────────

resource "google_compute_target_https_proxy" "frontend_https_proxy" {
  name             = "${var.project_name}-frontend-https-proxy"
  url_map          = google_compute_url_map.frontend_lb.id
  ssl_certificates = [google_compute_managed_ssl_certificate.frontend_ssl.id]
}

# ── HTTP proxy (redirect only) ─────────────────────────────────────────────────

resource "google_compute_target_http_proxy" "frontend_http_proxy" {
  name    = "${var.project_name}-frontend-http-proxy"
  url_map = google_compute_url_map.https_redirect.id
}

# ── Forwarding rules ──────────────────────────────────────────────────────────

resource "google_compute_global_forwarding_rule" "frontend_https" {
  name                  = "${var.project_name}-frontend-https"
  target                = google_compute_target_https_proxy.frontend_https_proxy.id
  port_range            = "443"
  ip_address            = google_compute_global_address.frontend_lb_ip.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

resource "google_compute_global_forwarding_rule" "frontend_http" {
  name                  = "${var.project_name}-frontend-http"
  target                = google_compute_target_http_proxy.frontend_http_proxy.id
  port_range            = "80"
  ip_address            = google_compute_global_address.frontend_lb_ip.id
  load_balancing_scheme = "EXTERNAL_MANAGED"
}

# ── Cloud DNS zone ─────────────────────────────────────────────────────────────

resource "google_dns_managed_zone" "sismicamarina" {
  name        = replace(var.domain, ".", "-")
  dns_name    = "${var.domain}."
  description = "Public DNS zone for ${var.domain}"
}

# ── DNS records ───────────────────────────────────────────────────────────────

resource "google_dns_record_set" "apex_a" {
  name         = "${var.domain}."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.sismicamarina.name
  rrdatas      = [google_compute_global_address.frontend_lb_ip.address]
}

resource "google_dns_record_set" "www_a" {
  name         = "www.${var.domain}."
  type         = "A"
  ttl          = 300
  managed_zone = google_dns_managed_zone.sismicamarina.name
  rrdatas      = [google_compute_global_address.frontend_lb_ip.address]
}
