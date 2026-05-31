const { buildDriver } = require('../utils/driverFactory');
const { By, until, Key } = require('selenium-webdriver');
const assert = require('assert');

describe('YouTube Homepage Tests', function () {
    this.timeout(60000);
    let driver;

    beforeEach(async function () {
        driver = await buildDriver();
    });

    afterEach(async function () {
        if (driver) await driver.quit();
    });

    it('TC01 - should have correct page title', async function () {
        await driver.get('https://www.youtube.com');
        const title = await driver.getTitle();
        assert.ok(title.includes('YouTube'), `Title should contain 'YouTube' but was: ${title}`);
    });

    it('TC02 - should have correct URL', async function () {
        await driver.get('https://www.youtube.com');
        const url = await driver.getCurrentUrl();
        assert.ok(url.includes('youtube.com'), `URL should contain 'youtube.com' but was: ${url}`);
    });

    it('TC03 - search should navigate to results page', async function () {
        await driver.get('https://www.youtube.com');
        const searchBox = await driver.wait(
            until.elementLocated(By.name('search_query')), 10000
        );
        await searchBox.sendKeys('Selenium WebDriver', Key.RETURN);
        await driver.wait(until.urlContains('search_query'), 10000);
        const url = await driver.getCurrentUrl();
        assert.ok(
            url.includes('search_query') || url.includes('results'),
            `URL should reflect search query but was: ${url}`
        );
    });

    it('TC04 - search result page title should contain search term', async function () {
        await driver.get('https://www.youtube.com');
        const searchBox = await driver.wait(
            until.elementLocated(By.name('search_query')), 10000
        );
        await searchBox.sendKeys('TestNG tutorial', Key.RETURN);
        await driver.wait(until.urlContains('search_query'), 10000);
        const title = await driver.getTitle();
        assert.ok(
            title.toLowerCase().includes('testng'),
            `Title should contain 'TestNG' but was: ${title}`
        );
    });

    it('TC05 - should open YouTube and verify homepage', async function () {
        await driver.get('https://www.youtube.com');
        const title = await driver.getTitle();
        const url   = await driver.getCurrentUrl();
        console.log('YouTube Title :', title);
        console.log('YouTube URL   :', url);
        assert.ok(url.includes('youtube.com'), `URL should contain 'youtube.com' but was: ${url}`);
        assert.ok(title.includes('YouTube'),   `Title should contain 'YouTube' but was: ${title}`);
    });
});
