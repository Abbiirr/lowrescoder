#!/usr/bin/env bash
set -euo pipefail

# Create source files
mkdir -p "src/my module"
echo 'print("hello from main")' > "src/my module/main.py"
echo 'print("hello from utils")' > "src/my module/utils.py"

# Create the broken build script
cat > build.sh << 'SCRIPT'
#!/usr/bin/env bash
# Build script - compile and package

SRC_DIR=src/my module
OUT_DIR=dist/output

# Create output directory
mkdir $OUT_DIR

# Get timestamp
BUILD_TIME=`date +%Y%m%d`

# Copy source files
cp -r $SRC_DIR/* $OUT_DIR/

# Run compilation
python3 -c "import compileall; compileall.compile_dir('$OUT_DIR')"

echo "Build complete at $BUILD_TIME"
SCRIPT
chmod +x build.sh

echo "Setup complete. build.sh has several bugs to fix."
