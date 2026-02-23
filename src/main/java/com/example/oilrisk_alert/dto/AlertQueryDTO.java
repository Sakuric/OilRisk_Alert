package com.example.oilrisk_alert.dto;

import lombok.Data;

@Data
public class AlertQueryDTO {
    private Integer page = 1;
    private Integer size = 20;
    private String level;
    private String sort = "date";
    private String order = "desc";
}
