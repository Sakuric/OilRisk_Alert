package com.example.oilrisk_alert.service.impl;

import com.example.oilrisk_alert.common.BusinessException;
import com.example.oilrisk_alert.dto.AlertQueryDTO;
import com.example.oilrisk_alert.entity.Alert;
import com.example.oilrisk_alert.mapper.AlertMapper;
import com.example.oilrisk_alert.service.AlertService;
import com.example.oilrisk_alert.vo.AlertDetailVO;
import com.example.oilrisk_alert.vo.AlertVO;
import com.example.oilrisk_alert.vo.PageVO;
import com.example.oilrisk_alert.vo.TriggerRuleVO;
import tools.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Set;

@Slf4j
@Service
@RequiredArgsConstructor
public class AlertServiceImpl implements AlertService {

    private final AlertMapper alertMapper;
    private final ObjectMapper objectMapper;

    private static final Set<String> VALID_LEVELS = Set.of("Low", "Medium", "High");
    private static final Set<String> VALID_SORT_FIELDS = Set.of("date", "riskIndex", "risk_index");
    private static final Set<String> VALID_ORDERS = Set.of("asc", "desc");

    @Override
    public PageVO<AlertVO> getAlerts(AlertQueryDTO query) {
        // Sanitize inputs
        String level = query.getLevel();
        if (level != null && !level.isEmpty() && !VALID_LEVELS.contains(level)) {
            level = null;
        }

        String sort = VALID_SORT_FIELDS.contains(query.getSort()) ? query.getSort() : "date";
        String order = VALID_ORDERS.contains(query.getOrder()) ? query.getOrder() : "desc";

        int page = Math.max(1, query.getPage());
        int size = Math.max(1, Math.min(100, query.getSize()));
        int offset = (page - 1) * size;

        long total = alertMapper.countByLevel(level);
        List<Alert> records = alertMapper.findPage(offset, size, level, sort, order);

        List<AlertVO> voList = new ArrayList<>(records.size());
        for (Alert alert : records) {
            AlertVO vo = new AlertVO();
            vo.setId(alert.getId());
            vo.setDate(alert.getDate().toString());
            vo.setLevel(alert.getLevel());
            vo.setRiskIndex(alert.getRiskIndex());
            vo.setTriggerType(alert.getTriggerType());
            vo.setTriggerFactor(alert.getTriggerFactor());
            vo.setTriggerFactorZh(alert.getTriggerFactorZh());
            vo.setSummary(alert.getSummary());
            vo.setSummaryEn(alert.getSummaryEn());
            vo.setAiReport(alert.getAiReport());
            voList.add(vo);
        }

        PageVO<AlertVO> pageVO = new PageVO<>();
        pageVO.setTotal(total);
        pageVO.setPage(page);
        pageVO.setSize(size);
        pageVO.setRecords(voList);

        return pageVO;
    }

    @Override
    public AlertDetailVO getAlertDetail(Long id) {
        Alert alert = alertMapper.findById(id);
        if (alert == null) {
            throw new BusinessException(404, "Alert not found: " + id);
        }

        AlertDetailVO vo = new AlertDetailVO();
        vo.setId(alert.getId());
        vo.setDate(alert.getDate().toString());
        vo.setLevel(alert.getLevel());
        vo.setRiskIndex(alert.getRiskIndex());
        vo.setTriggerType(alert.getTriggerType());
        vo.setTriggerFactor(alert.getTriggerFactor());
        vo.setTriggerFactorZh(alert.getTriggerFactorZh());
        vo.setSummary(alert.getSummary());
        vo.setSummaryEn(alert.getSummaryEn());

        List<TriggerRuleVO> triggerRules = Collections.emptyList();
        if (alert.getDetail() != null && !alert.getDetail().isEmpty()) {
            try {
                triggerRules = objectMapper.readValue(alert.getDetail(),
                        objectMapper.getTypeFactory().constructCollectionType(
                                List.class, TriggerRuleVO.class));
            } catch (Exception e) {
                log.warn("Failed to parse alert detail JSON for alert {}: {}",
                        id, e.getMessage());
                triggerRules = Collections.emptyList();
            }
        }
        vo.setTriggerRules(triggerRules);

        return vo;
    }
}
