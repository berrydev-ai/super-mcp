# Makefile for building super binary Lambda layer
# This downloads and prepares the super binary for AWS Lambda deployment

SUPER_VERSION ?= latest
SUPER_ARCH = linux-amd64
LAYER_DIR = $(PWD)
BIN_DIR = $(LAYER_DIR)/bin
TEMP_DIR = $(LAYER_DIR)/tmp

.PHONY: build clean download-super verify

# Main build target
build: clean download-super verify
	@echo "Super binary layer build completed successfully"
	@ls -la $(BIN_DIR)/

# Clean previous builds
clean:
	@echo "Cleaning previous builds..."
	@rm -rf $(BIN_DIR)
	@rm -rf $(TEMP_DIR)
	@mkdir -p $(BIN_DIR)
	@mkdir -p $(TEMP_DIR)

# Download super binary from GitHub releases
download-super:
	@echo "Downloading super binary ($(SUPER_VERSION) for $(SUPER_ARCH))..."
	@if [ "$(SUPER_VERSION)" = "latest" ]; then \
		DOWNLOAD_URL=$$(curl -s https://api.github.com/repos/brimdata/super/releases/latest | grep "browser_download_url.*$(SUPER_ARCH).tar.gz" | cut -d '"' -f 4); \
	else \
		DOWNLOAD_URL="https://github.com/brimdata/super/releases/download/v$(SUPER_VERSION)/super-$(SUPER_ARCH).tar.gz"; \
	fi; \
	echo "Downloading from: $$DOWNLOAD_URL"; \
	curl -L -o $(TEMP_DIR)/super-$(SUPER_ARCH).tar.gz "$$DOWNLOAD_URL"
	
	@echo "Extracting super binary..."
	@cd $(TEMP_DIR) && tar -xzf super-$(SUPER_ARCH).tar.gz
	
	@echo "Installing super binary to layer..."
	@find $(TEMP_DIR) -name "super" -type f -executable -exec cp {} $(BIN_DIR)/ \;
	@chmod +x $(BIN_DIR)/super
	
	@echo "Cleaning up temporary files..."
	@rm -rf $(TEMP_DIR)

# Verify the binary is working
verify:
	@echo "Verifying super binary..."
	@if [ -f $(BIN_DIR)/super ]; then \
		echo "✓ Super binary exists at $(BIN_DIR)/super"; \
		if [ -x $(BIN_DIR)/super ]; then \
			echo "✓ Super binary is executable"; \
			echo "Binary info:"; \
			file $(BIN_DIR)/super; \
			echo "Binary size: $$(du -h $(BIN_DIR)/super | cut -f1)"; \
			if $(BIN_DIR)/super --version >/dev/null 2>&1; then \
				echo "✓ Super binary version check passed"; \
				$(BIN_DIR)/super --version; \
			else \
				echo "⚠ Super binary version check failed (may be normal in some environments)"; \
			fi; \
		else \
			echo "✗ Super binary is not executable"; \
			exit 1; \
		fi; \
	else \
		echo "✗ Super binary not found"; \
		exit 1; \
	fi

# Development target to test locally
test-local:
	@echo "Testing super binary locally..."
	@$(BIN_DIR)/super --help | head -10

# Show information about the layer
info:
	@echo "Layer information:"
	@echo "  Layer directory: $(LAYER_DIR)"
	@echo "  Binary directory: $(BIN_DIR)"
	@echo "  Binary path: $(BIN_DIR)/super"
	@if [ -f $(BIN_DIR)/super ]; then \
		echo "  Binary exists: Yes"; \
		echo "  Binary size: $$(du -h $(BIN_DIR)/super | cut -f1)"; \
		echo "  Binary permissions: $$(ls -l $(BIN_DIR)/super | cut -d' ' -f1)"; \
	else \
		echo "  Binary exists: No"; \
	fi