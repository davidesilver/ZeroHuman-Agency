#!/bin/bash
# Quick test script for Humanizer integration

set -e

cd "$(dirname "$0")/python"

echo "🧪 Testing Humanizer Integration..."
echo ""

echo "1️⃣  Running unit tests..."
python -m pytest tests/test_humanizer.py -v --tb=short

echo ""
echo "2️⃣  Running integration tests..."
python -m pytest tests/test_humanizer_integration.py -v --tb=short

echo ""
echo "3️⃣  Checking imports..."
python -c "
from content_engine.agents.humanizer import humanize_draft
from content_engine.orchestrator.content import generate_and_god_and_humanize
print('✅ All imports successful')
"

echo ""
echo "4️⃣  Verifying prompt file exists..."
if [ -f "src/content_engine/prompts/skills/humanizer_skill.md" ]; then
    LINES=$(wc -l < "src/content_engine/prompts/skills/humanizer_skill.md")
    echo "✅ humanizer_skill.md found ($LINES lines)"
else
    echo "❌ humanizer_skill.md not found!"
    exit 1
fi

echo ""
echo "5️⃣  Verifying API routes..."
python -c "
import sys
sys.path.insert(0, 'src')
from content_engine.api.routes import router
routes = [route.path for route in router.routes]
if '/content/drafts/{draft_id}/humanize' in routes:
    print('✅ Humanizer API endpoint registered')
else:
    print('❌ Humanizer API endpoint not found!')
    sys.exit(1)
"

echo ""
echo "✅ All tests passed! Humanizer is ready to use."
echo ""
echo "📝 Next steps:"
echo "   1. Update brand settings in Supabase to enable humanizer"
echo "   2. Set use_humanizer = TRUE for your brand"
echo "   3. Configure humanizer_channels (e.g., ARRAY['linkedin', 'blog'])"
echo "   4. Test via API: POST /api/content/generate with run_humanizer=true"
