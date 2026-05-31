package com.selenium.utils;

import org.apache.poi.ss.usermodel.*;
import org.apache.poi.xssf.usermodel.XSSFWorkbook;

import java.io.FileInputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.List;

public class ExcelReader {

    private final String filePath;
    private Workbook workbook;

    public ExcelReader(String filePath) {
        this.filePath = filePath;
    }

    public void open() throws IOException {
        FileInputStream fis = new FileInputStream(filePath);
        workbook = new XSSFWorkbook(fis);
    }

    public void close() throws IOException {
        if (workbook != null) workbook.close();
    }

    public String getCellValue(String sheetName, int row, int col) {
        Sheet sheet = workbook.getSheet(sheetName);
        Row r = sheet.getRow(row);
        if (r == null) return "";
        Cell cell = r.getCell(col);
        if (cell == null) return "";
        return new DataFormatter().formatCellValue(cell);
    }

    public List<String[]> getSheetData(String sheetName) {
        Sheet sheet = workbook.getSheet(sheetName);
        List<String[]> data = new ArrayList<>();
        DataFormatter formatter = new DataFormatter();
        for (Row row : sheet) {
            int cellCount = row.getLastCellNum();
            String[] rowData = new String[cellCount];
            for (int i = 0; i < cellCount; i++) {
                Cell cell = row.getCell(i);
                rowData[i] = cell != null ? formatter.formatCellValue(cell) : "";
            }
            data.add(rowData);
        }
        return data;
    }

    // Returns a 2D Object[][] suitable for use as a TestNG @DataProvider
    public Object[][] getDataProviderData(String sheetName) {
        List<String[]> rows = getSheetData(sheetName);
        Object[][] data = new Object[rows.size()][];
        for (int i = 0; i < rows.size(); i++) {
            data[i] = rows.get(i);
        }
        return data;
    }
}
