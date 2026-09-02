import { HttpClient } from '@angular/common/http';
import { Component, Input, Output, EventEmitter, OnChanges, OnInit, OnDestroy, SimpleChanges } from '@angular/core';
import { environment } from 'src/environments/environment';

@Component({
  selector: 'app-mainstatus',
  templateUrl: './mainstatus.component.html',
  styleUrls: ['./mainstatus.component.css']
})

export class MainstatusComponent implements OnInit, OnChanges, OnDestroy {
  @Input() meterData: any;
  @Input() allData: any;
  @Input() ESGData: any;
  @Input() IAQ: any;
  @Input() OAQ: any;
  @Input() outdoorMode: any;
  @Output() screenChanged = new EventEmitter<number>();
  
  currentScreen: number = 0;
  totalScreens: number = 4;
  readonly aqiGaugeRadius = 70;
  readonly aqiGaugeCircumference = 2 * Math.PI * 70;
  private intervalId: any;

  constructor(private http: HttpClient) {
  }

  ngOnChanges(changes: SimpleChanges): void {
  }

  ngOnInit(): void {
    console.log("meterData",this.allData);
  }

  ngOnDestroy(): void {
    if (this.intervalId) {
        clearInterval(this.intervalId);
    }
  }

  nextScreen() {
    if (this.currentScreen < this.totalScreens - 1) {
      this.currentScreen++;
      this.screenChanged.emit(this.currentScreen);
    }
  }

  prevScreen() {
    if (this.currentScreen > 0) {
      this.currentScreen--;
      this.screenChanged.emit(this.currentScreen);
    }
  }

  readonly reservoirCapacityLiters = 40;

  get reservoirFillPercent(): number {
    const hasError = this.allData?.alarm?.ultrasonic_error == 1;
    const liters = this.allData?.data?.ultrasonic;
    if (hasError || liters === undefined || liters === null || liters === '') {
      return 0;
    }
    const percent = (Number(liters) / this.reservoirCapacityLiters) * 100;
    return Math.min(Math.max(percent, 0), 100);
  }
  get reservoirFillColor(): string {
    const state = this.meterData?.water[0];
    if (state === "0") return '#a4241d';
    if (state === "1") return '#ffc956';
    if (state === "2") return '#317b04';
    return '#234c9f';
  }

  private aqiRating(aqi: number) {
    if (aqi <= 50) return { ring: '#00e400', txt: 'Good', bg: '#d4edda', fg: '#155724' };
    if (aqi <= 100) return { ring: '#ffff00', txt: 'Moderate', bg: '#fff9c4', fg: '#827717' };
    if (aqi <= 150) return { ring: '#ff7e00', txt: 'Unhealthy', bg: '#ffe0b2', fg: '#e65100' };
    if (aqi <= 200) return { ring: '#ff0000', txt: 'Unhealthy', bg: '#ffcdd2', fg: '#b71c1c' };
    if (aqi <= 300) return { ring: '#8f3f97', txt: 'Very Unhealthy', bg: '#e1bee7', fg: '#4a148c' };
    return { ring: '#7e0023', txt: 'Hazardous', bg: '#f8bbd0', fg: '#880e4f' };
  }

  get aqiValue(): number {
    const aqi = this.IAQ?.aqi || 0;
    return aqi
  }

  get aqiData() {
    return this.aqiRating(this.aqiValue);
  }

  get outdoorAqiValue(): number {
    return this.OAQ?.aqi || 0;
  }
  get outdoormode(): number {
    return this.outdoorMode || 0;
  }
  get outdoorAqiData() {
    return this.aqiRating(this.outdoorAqiValue);
  }

  get aqiDiffPercent(): number {
    const outdoor = this.outdoorAqiValue;
    if (!outdoor) return 0;
    return Math.round(((outdoor - this.aqiValue) / outdoor) * 100);
  }

  get aqiDiffAbsPercent(): number {
    const indoor = this.aqiValue || 0;
    const outdoor = this.outdoorAqiValue || 0;

    const higherValue = Math.max(indoor, outdoor);

    if (higherValue === 0) return 0;

    return Math.round(
      (Math.abs(indoor - outdoor) / higherValue) * 100
    );
  }

  get aqiIndoorIsCleaner(): boolean {
    return this.aqiValue < this.outdoorAqiValue;
  }

  get aqiGaugePercent(): number {
    const percent = (this.aqiValue / 300) * 100;
    return Math.min(Math.max(percent, 0), 100);
  }

  get oaqGaugePercent(): number {
    const percent = (this.outdoorAqiValue/300)*100;
    return Math.min(Math.max(percent,0),100)
  }

  get aqiGaugeDashOffset(): number {
    return this.aqiGaugeCircumference - (this.aqiGaugePercent / 100) * this.aqiGaugeCircumference;
  }

  get oaqGaugeDashOffset(): number {
    return this.aqiGaugeCircumference - (this.oaqGaugePercent / 100) * this.aqiGaugeCircumference;
  }

  get waterDispenserEquivalent(): number {
    const saved = this.ESGData?.total_water_saved || 0;
    return Math.round(saved / 20);
  }

  private classify(value: number | null | undefined, excellentMax: number, goodMax: number, moderateMax: number) {
    if (value === null || value === undefined) {
      return { txt: '-', bg: '#f3f4f6', fg: '#6b7280' };
    }
    if (value <= excellentMax) return { txt: 'EXCELLENT', bg: '#dcfce7', fg: '#16a34a' };
    if (value <= goodMax) return { txt: 'GOOD', bg: '#dbeafe', fg: '#2563eb' };
    if (value <= moderateMax) return { txt: 'MODERATE', bg: '#ffedd5', fg: '#d97706' };
    return { txt: 'POOR', bg: '#fee2e2', fg: '#dc2626' };
  }
  // indoor parameters
  get pm25Status() {
    return this.classify(this.IAQ?.pm2p5, 5, 15, 25);
  }
  get co2Status() {
    return this.classify(this.IAQ?.co2, 800, 1000, 1500);
  }
  get vocStatus() {
    return this.classify(this.IAQ?.voc, 50, 100, 200);
  }
  // outdoor parameters
  get outpm25Status() {
    return this.classify(this.OAQ?.pm2p5, 5, 15, 25);
  }
  get outco2Status() {
    return this.classify(this.OAQ?.co2, 800, 1000, 1500);
  }
  get outcoStatus() {
    return this.classify(this.OAQ?.co, 800, 1000, 1500);
  }

  flippedCards: { [key: string]: boolean } = {};

  toggleCardFlip(cardKey: string) {
    this.flippedCards[cardKey] = !this.flippedCards[cardKey];
  }
}
