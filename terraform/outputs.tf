output "backend_url" {
  description = "Backend Cloud Run service URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Frontend Cloud Run service URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "load_balancer_ip" {
  description = "Static IP of the global HTTPS load balancer"
  value       = google_compute_global_address.frontend_lb_ip.address
}

output "dns_nameservers" {
  description = "Google Cloud DNS nameservers — set these at your domain registrar (nic.cl)"
  value       = google_dns_managed_zone.sismicamarina.name_servers
}

output "site_url" {
  description = "Public site URL"
  value       = "https://${var.domain}"
}
