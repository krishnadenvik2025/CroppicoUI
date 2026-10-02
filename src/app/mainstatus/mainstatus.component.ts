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
  @Output() screenChanged = new EventEmitter<number>();
  
  currentScreen: number = 0;
  totalScreens: number = 1;
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
}
