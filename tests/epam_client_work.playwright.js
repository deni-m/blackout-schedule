// Playwright scenario for EPAM Client Work verification
// Run environment expects Playwright to be available in MCP tool

module.exports = async (page) => {
  // Step 1: Navigate to EPAM
  await page.goto('https://www.epam.com/', { waitUntil: 'domcontentloaded', timeout: 60000 });

  // Handle cookie consent if present
  try {
    const consentButton = await page.locator('button:has-text("Accept All")');
    if (await consentButton.first().isVisible({ timeout: 3000 })) {
      await consentButton.first().click({ timeout: 5000 });
    }
  } catch (e) { /* ignore if not present */ }

  // Step 2: Try to open Services menu (fallback to What We Do)
  const possibleMenus = [
    'header >> text=Services',
    'header >> text=What We Do',
    'nav[role="navigation"] >> text=Services',
    'nav[role="navigation"] >> text=What We Do',
  ];

  let openedMenu = false;
  for (const selector of possibleMenus) {
    try {
      const el = page.locator(selector).first();
      if (await el.isVisible({ timeout: 3000 })) {
        await el.hover();
        await page.waitForTimeout(500);
        openedMenu = true;
        break;
      }
    } catch { /* try next */ }
  }

  if (!openedMenu) {
    throw new Error('Could not find Services/What We Do menu in header');
  }

  // Step 3: Click "Explore Our Client Work"
  const exploreSelectors = [
    'text=/^Explore Our Client Work$/i',
    'a:has-text("Explore Our Client Work")',
    'text=/Client Work/i'
  ];

  let clickedExplore = false;
  for (const sel of exploreSelectors) {
    const link = page.locator(sel).first();
    if (await link.count()) {
      try {
        await link.click({ timeout: 10000 });
        clickedExplore = true;
        break;
      } catch { /* continue */ }
    }
  }

  if (!clickedExplore) {
    throw new Error('Could not locate "Explore Our Client Work" link');
  }

  // Step 4: Verify "Client Work" text is visible
  await page.waitForLoadState('domcontentloaded');
  const clientWorkVisible = await page.locator('text=/Client Work/i').first().isVisible({ timeout: 20000 });
  if (!clientWorkVisible) {
    throw new Error('"Client Work" text not visible on the page');
  }

  return 'Client Work text verified as visible.';
};