#!/usr/bin/env bash
set -e

cd /app/microservices

echo "[*] Running API documentation generation tests..."

# Check if OpenAPI specification exists
if [ ! -f "openapi.yaml" ] && [ ! -f "openapi.json" ] && [ ! -f "docs/openapi.yaml" ] && [ ! -f "docs/openapi.json" ]; then
    echo "[✗] ERROR: OpenAPI specification not found"
    echo "    Expected: openapi.yaml or openapi.json in root or docs/ directory"
    exit 1
fi

OPENAPI_FILE=""
for file in openapi.yaml openapi.json docs/openapi.yaml docs/openapi.json; do
    if [ -f "$file" ]; then
        OPENAPI_FILE="$file"
        echo "[✓] Found OpenAPI specification: $file"
        break
    fi
done

# Validate OpenAPI specification
echo "[*] Validating OpenAPI specification..."

if python3 -c "import yaml, json; f=open('$OPENAPI_FILE'); data=yaml.safe_load(f) if '$OPENAPI_FILE'.endswith('.yaml') else json.load(f); assert data.get('openapi') or data.get('swagger'), 'Invalid OpenAPI spec'" 2>/dev/null; then
    echo "[✓] OpenAPI specification is valid"
else
    echo "[!] WARNING: OpenAPI specification validation may have issues"
fi

# Check for required OpenAPI 3.0 structure
echo "[*] Checking OpenAPI 3.0 structure..."

python3 << 'EOF'
import yaml
import json
import sys

openapi_file = None
for f in ['openapi.yaml', 'openapi.json', 'docs/openapi.yaml', 'docs/openapi.json']:
    try:
        with open(f, 'r') as file:
            if f.endswith('.yaml'):
                spec = yaml.safe_load(file)
            else:
                spec = json.load(file)
            openapi_file = f
            break
    except:
        continue

if not openapi_file:
    print("[✗] ERROR: Could not read OpenAPI specification")
    sys.exit(1)

# Check OpenAPI version
version = spec.get('openapi') or spec.get('swagger')
if not version:
    print("[✗] ERROR: OpenAPI version not specified")
    sys.exit(1)

if not version.startswith('3.'):
    print(f"[!] WARNING: OpenAPI version is {version}, expected 3.x")
else:
    print(f"[✓] OpenAPI version: {version}")

# Check for required sections
required_sections = ['info', 'paths']
missing = [s for s in required_sections if s not in spec]
if missing:
    print(f"[✗] ERROR: Missing required sections: {', '.join(missing)}")
    sys.exit(1)

print("[✓] Required sections present")

# Check for paths
paths = spec.get('paths', {})
if not paths:
    print("[✗] ERROR: No API paths defined")
    sys.exit(1)

print(f"[✓] Found {len(paths)} API path(s)")

# Check for endpoints from the codebase
expected_paths = [
    '/api/users',
    '/api/users/{id}',
    '/api/orders',
    '/api/orders/{order_id}',
    '/api/auth/login',
    '/api/auth/register',
    '/api/auth/refresh'
]

found_paths = []
for expected in expected_paths:
    # Try different path formats
    variations = [
        expected,
        expected.replace('{id}', '{userId}'),
        expected.replace('{order_id}', '{orderId}'),
    ]
    for var in variations:
        if var in paths:
            found_paths.append(expected)
            break

print(f"[✓] Found {len(found_paths)}/{len(expected_paths)} expected endpoints")

if len(found_paths) < len(expected_paths) * 0.7:  # At least 70% coverage
    print("[!] WARNING: Some expected endpoints may be missing")
EOF

# Check for Swagger UI
echo "[*] Checking for Swagger UI..."

if [ -d "docs/swagger-ui" ] || [ -f "docs/index.html" ] || [ -f "swagger-ui.html" ] || [ -f "docs/swagger.html" ]; then
    echo "[✓] Swagger UI found"
else
    echo "[!] WARNING: Swagger UI may not be set up"
    echo "    Expected: Interactive Swagger UI documentation"
fi

# Check for example requests/responses
echo "[*] Checking for example requests and responses..."

python3 << 'EOF'
import yaml
import json
import sys

openapi_file = None
for f in ['openapi.yaml', 'openapi.json', 'docs/openapi.yaml', 'docs/openapi.json']:
    try:
        with open(f, 'r') as file:
            if f.endswith('.yaml'):
                spec = yaml.safe_load(file)
            else:
                spec = json.load(file)
            openapi_file = f
            break
    except:
        continue

if not openapi_file:
    sys.exit(1)

examples_found = 0
paths = spec.get('paths', {})

for path, methods in paths.items():
    for method, details in methods.items():
        if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
            # Check for examples in request body
            if 'requestBody' in details:
                content = details['requestBody'].get('content', {})
                for content_type, schema in content.items():
                    if 'example' in schema or 'examples' in schema:
                        examples_found += 1
            
            # Check for examples in responses
            if 'responses' in details:
                for status, response in details['responses'].items():
                    content = response.get('content', {})
                    for content_type, schema in content.items():
                        if 'example' in schema or 'examples' in schema:
                            examples_found += 1

if examples_found > 0:
    print(f"[✓] Found examples in {examples_found} endpoint(s)")
else:
    print("[!] WARNING: No examples found in OpenAPI specification")
EOF

# Check for client SDKs
echo "[*] Checking for client SDKs..."

SDK_FOUND=false

# Check for Python SDK
if [ -d "sdk/python" ] || [ -d "sdks/python" ] || [ -f "python-sdk.zip" ] || [ -d "clients/python" ]; then
    echo "[✓] Python SDK found"
    SDK_FOUND=true
fi

# Check for JavaScript SDK
if [ -d "sdk/javascript" ] || [ -d "sdk/js" ] || [ -d "sdks/javascript" ] || [ -f "javascript-sdk.zip" ] || [ -d "clients/javascript" ] || [ -d "clients/js" ]; then
    echo "[✓] JavaScript SDK found"
    SDK_FOUND=true
fi

if [ "$SDK_FOUND" = false ]; then
    echo "[!] WARNING: Client SDKs may not be generated"
    echo "    Expected: Python and JavaScript SDKs"
fi

# Check for getting-started guide
echo "[*] Checking for getting-started guide..."

if [ -f "GETTING_STARTED.md" ] || [ -f "docs/GETTING_STARTED.md" ] || [ -f "getting-started.md" ] || [ -f "docs/getting-started.md" ]; then
    echo "[✓] Getting-started guide found"
    
    # Check if it contains authentication examples
    GUIDE_FILE=""
    for f in GETTING_STARTED.md docs/GETTING_STARTED.md getting-started.md docs/getting-started.md; do
        if [ -f "$f" ]; then
            GUIDE_FILE="$f"
            break
        fi
    done
    
    if [ -n "$GUIDE_FILE" ]; then
        if grep -qi "auth\|token\|bearer\|login\|authentication" "$GUIDE_FILE"; then
            echo "[✓] Getting-started guide contains authentication examples"
        else
            echo "[!] WARNING: Getting-started guide may not include authentication examples"
        fi
    fi
else
    echo "[!] WARNING: Getting-started guide not found"
    echo "    Expected: GETTING_STARTED.md or docs/getting-started.md"
fi

# Check for endpoint coverage
echo "[*] Checking endpoint coverage..."

python3 << 'EOF'
import yaml
import json
import sys

openapi_file = None
for f in ['openapi.yaml', 'openapi.json', 'docs/openapi.yaml', 'docs/openapi.json']:
    try:
        with open(f, 'r') as file:
            if f.endswith('.yaml'):
                spec = yaml.safe_load(file)
            else:
                spec = json.load(file)
            openapi_file = f
            break
    except:
        continue

if not openapi_file:
    sys.exit(1)

paths = spec.get('paths', {})
methods_count = 0

for path, methods in paths.items():
    for method in methods.keys():
        if method.lower() in ['get', 'post', 'put', 'delete', 'patch']:
            methods_count += 1

print(f"[✓] Documented {methods_count} HTTP method(s) across {len(paths)} path(s)")

# Check for security schemes
if 'components' in spec and 'securitySchemes' in spec['components']:
    print("[✓] Security schemes defined")
else:
    print("[!] WARNING: Security schemes may not be defined")
EOF

echo "[✓] All tests completed!"
exit 0
