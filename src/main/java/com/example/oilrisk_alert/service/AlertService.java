package com.example.oilrisk_alert.service;

import com.example.oilrisk_alert.dto.AlertQueryDTO;
import com.example.oilrisk_alert.vo.AlertDetailVO;
import com.example.oilrisk_alert.vo.AlertVO;
import com.example.oilrisk_alert.vo.PageVO;

public interface AlertService {

    PageVO<AlertVO> getAlerts(AlertQueryDTO query);

    AlertDetailVO getAlertDetail(Long id);
}
