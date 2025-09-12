# Multi-stage build for React frontend
FROM node:18-alpine as build

# Set npm configuration for ARM64 compatibility
RUN npm config set registry https://registry.npmjs.org/

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Remove package-lock.json and node_modules to fix ARM64 rollup issue
RUN rm -rf package-lock.json node_modules

# Install dependencies with clean install
RUN npm install

# Copy source code
COPY . .

# Build the application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose port 3000
EXPOSE 3000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:3000/ || exit 1

# Start nginx
CMD ["nginx", "-g", "daemon off;"]
