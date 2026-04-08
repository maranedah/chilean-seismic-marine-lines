/** @type {import('next').NextConfig} */
const nextConfig = {
  webpack: (config) => {
    config.watchOptions = {
      poll: 1000,       // check for changes every 1 s (required on Windows/Docker)
      aggregateTimeout: 300,
    }
    return config
  },
  // Proxying to the backend is handled in src/middleware.ts at runtime so that
  // BACKEND_URL is read from the running container's environment rather than
  // being baked in during `next build`.
}

export default nextConfig
