package com.selenium.tests;

import com.selenium.base.BaseTest;
import com.selenium.pages.GoogleHomePage;
import org.openqa.selenium.WebDriver;
import org.testng.Assert;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;

public class GoogleHomeTest extends BaseTest {

    @Test(description = "TC01 - Verify Google homepage title")
    public void verifyTitle() {
        GoogleHomePage page = new GoogleHomePage();
        page.open();
        Assert.assertTrue(page.getTitle().contains("Google"),
            "Title should contain 'Google'");
    }

    @Test(description = "TC02 - Verify Google homepage URL")
    public void verifyUrl() {
        GoogleHomePage page = new GoogleHomePage();
        page.open();
        Assert.assertTrue(page.getCurrentUrl().contains("google.com"),
            "URL should contain 'google.com'");
    }

    @Test(description = "TC03 - Verify search navigates to results page")
    public void verifySearch() {
        GoogleHomePage page = new GoogleHomePage();
        page.open();
        page.searchFor("Selenium WebDriver");
        String url = page.getCurrentUrl();
        Assert.assertTrue(url.contains("search") || url.contains("q="),
            "URL should reflect the search query but was: " + url);
    }

    @DataProvider(name = "searchTerms")
    public Object[][] searchTerms() {
        return new Object[][] {
            { "Selenium WebDriver" },
            { "TestNG tutorial" },
            { "Apache POI Excel" }
        };
    }

    @Test(description = "TC04 - Data-driven search with multiple terms",
          dataProvider = "searchTerms")
    public void verifyDataDrivenSearch(String searchTerm) {
        GoogleHomePage page = new GoogleHomePage();
        page.open();
        page.searchFor(searchTerm);
        String url = page.getCurrentUrl();
        Assert.assertTrue(url.contains("search") || url.contains("q="),
            "Search for '" + searchTerm + "' should land on results page");
    }

    @Test(description = "TC05 - Open YouTube and verify homepage")
    public void openYouTube() {
        driver.get("https://www.youtube.com");

        String title = driver.getTitle();
        String url   = driver.getCurrentUrl();

        System.out.println("YouTube Title : " + title);
        System.out.println("YouTube URL   : " + url);

        Assert.assertTrue(url.contains("youtube.com"),
            "URL should contain 'youtube.com' but was: " + url);
        Assert.assertTrue(title.contains("YouTube"),
            "Title should contain 'YouTube' but was: " + title);
    }
}
