package com.selenium.pages;

import org.openqa.selenium.By;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;

public class GoogleHomePage extends BasePage {

    private static final String URL = "https://www.google.com";

    private final By searchInput  = By.name("q");
    private final By consentBtn   = By.cssSelector("#L2AGLb, .sy4vM, button[id*='accept'], [aria-label*='Accept']");

    public void open() {
        navigateTo(URL);
        acceptConsentIfPresent();
    }

    private void acceptConsentIfPresent() {
        try {
            Thread.sleep(1500);
            driver.findElement(consentBtn).click();
            Thread.sleep(500);
        } catch (Exception ignored) {
        }
    }

    public void searchFor(String query) {
        String encoded = URLEncoder.encode(query, StandardCharsets.UTF_8);
        navigateTo("https://www.google.com/search?q=" + encoded);
    }

    public void clickSearchButton() {
        click(By.name("btnK"));
    }
}
