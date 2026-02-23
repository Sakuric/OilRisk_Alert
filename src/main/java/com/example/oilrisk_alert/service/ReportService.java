package com.example.oilrisk_alert.service;

import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

public interface ReportService {

    SseEmitter generateReport(Long alertId);
}
